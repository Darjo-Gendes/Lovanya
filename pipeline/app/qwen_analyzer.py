import json

import torch
from qwen_vl_utils import process_vision_info
from transformers import AutoModelForImageTextToText, AutoProcessor

import os

from .. import config
from .json_utils import extract_json


def resolve_adapter(setting: str) -> str:
    """Resolve the ADAPTER config: explicit path, 'auto' (newest dir under
    pipeline/adapters/ by mtime), or '' for the base model."""
    if not setting:
        return ""
    if setting != "auto":
        return setting
    adapters_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "adapters"
    )
    if not os.path.isdir(adapters_dir):
        return ""
    dirs = [
        os.path.join(adapters_dir, d)
        for d in os.listdir(adapters_dir)
        if os.path.isdir(os.path.join(adapters_dir, d))
        and os.path.exists(os.path.join(adapters_dir, d, "adapter_config.json"))
    ]
    if not dirs:
        return ""
    return max(dirs, key=os.path.getmtime)


PERCEIVE_PROMPT = """Look at this outfit photo. Respond with ONLY a JSON object
(no markdown fences, no commentary) with these keys:
{
  "garment_category": "e.g. dress, top+bottom, suit, activewear, ...",
  "items": ["short description of each visible garment/accessory"],
  "dominant_colors": ["2-4 dominant colors you actually see, plain color names"],
  "pattern": "solid | striped | floral | plaid | graphic | other, describe briefly",
  "silhouette": "fitted | loose | mixed, describe briefly",
  "modest_dress": "true if the outfit signals modest dress (hijab, covered arms, long hemlines, deliberate loose layering), else false",
  "notes": "anything unusual (blurry photo, no person visible, partial outfit, etc.)"
}
If no clear outfit is visible, still return this JSON shape but say so in "notes"
and leave other fields as your best honest guess."""

JUDGE_PROMPT_TEMPLATE = """You are judging this outfit using the styling
framework below. The occasion is: {occasion}

--- STYLING FRAMEWORK ---
{framework}
--- END FRAMEWORK ---

Perception data already extracted from this same photo:
{perception}

Respond with ONLY a JSON object (no markdown fences, no commentary) matching
the "Output contract" section of the framework above."""


class QwenAnalyzer:
    """Perception + judgment via Qwen VL, one structured call per stage.

    No chat/multi-turn history is kept between calls - each perceive()/judge()
    call is an independent one-shot inference, per the locked architecture
    decision to keep per-action cost bounded.
    """

    input_kind = "image"  # analyze() dispatches on this: photo, not palette

    def __init__(self, model_id: str | None = None):
        model_id = model_id or config.QWEN_MODEL_ID
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        kwargs = {"dtype": "auto", "device_map": "auto"}
        if config.QUANT == "4bit" and self.device == "cuda":
            from transformers import BitsAndBytesConfig

            kwargs["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.bfloat16,
            )
            # auto device-map estimates spill to CPU (disallowed for 4-bit);
            # NF4-quantized the model fits on the card, so pin it there.
            kwargs["device_map"] = {"": 0}
        self.model = AutoModelForImageTextToText.from_pretrained(model_id, **kwargs)
        adapter = resolve_adapter(config.ADAPTER)
        if adapter:
            from peft import PeftModel

            self.model = PeftModel.from_pretrained(self.model, adapter)
        self.adapter = adapter
        self.processor = AutoProcessor.from_pretrained(model_id)

    def _generate(self, image_path: str, prompt: str, max_new_tokens: int) -> str:
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image_path},
                    {"type": "text", "text": prompt},
                ],
            }
        ]
        chat_text = self.processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        image_inputs, video_inputs = process_vision_info(messages)
        inputs = self.processor(
            text=[chat_text],
            images=image_inputs,
            videos=video_inputs,
            padding=True,
            return_tensors="pt",
        ).to(self.model.device)

        generated_ids = self.model.generate(**inputs, max_new_tokens=max_new_tokens)
        trimmed = [
            out_ids[len(in_ids) :]
            for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
        ]
        return self.processor.batch_decode(
            trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
        )[0]

    def perceive(self, image_path: str) -> dict:
        raw = self._generate(image_path, PERCEIVE_PROMPT, max_new_tokens=300)
        return extract_json(raw)

    def judge(self, image_path: str, perception: dict, occasion: str) -> dict:
        with open(config.FRAMEWORK_PATH, encoding="utf-8") as f:
            framework = f.read()
        prompt = JUDGE_PROMPT_TEMPLATE.format(
            occasion=occasion,
            framework=framework,
            perception=json.dumps(perception, ensure_ascii=False),
        )
        raw = self._generate(image_path, prompt, max_new_tokens=400)
        return extract_json(raw)
