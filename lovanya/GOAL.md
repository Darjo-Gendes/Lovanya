# Loványa — Definition of Done

The MVP is complete when ALL of the following are true. Once they are, stop adding
features and focus only on refinement. Unnecessary complexity is a product failure.

1. **Photo input** — A user can take a photo of themselves or their clothing
   (camera capture or upload).
2. **Automatic wardrobe** — The AI identifies, organizes, and stores wardrobe
   items automatically (no manual tagging required; user may correct).
3. **Outfit recommendations** — The AI recommends complete outfits assembled
   from the user's own wardrobe.
4. **Explainability** — The AI explains WHY an outfit is recommended, in warm,
   specific language referencing real colors/occasion/weather.
5. **Memory** — The AI remembers user preferences (loved items, accepted and
   rejected recommendations, color bias) and recommendations improve over time.
6. **Stylist, not database** — The experience feels like a personal stylist:
   guidance-first, never a grid of metadata.
7. **30-second value** — A first-time user gets value within 30 seconds of
   opening the app.
8. **Premium feel** — The product feels premium, elegant, and emotionally
   supportive (gentle copy, never judgmental).
9. **Buildable** — The MVP is realistically maintainable by a small startup
   team: one Next.js app, localStorage persistence, one swappable AI service,
   no backend.
10. **Four excellent core experiences** —
    - Outfit Analysis (Outfit Check)
    - Wardrobe Organization (Closet)
    - Outfit Recommendation (Style Me)
    - Aura Companion (ambient presence throughout)

## Guardrails

- Do not invent additional features after the goal is achieved.
- Prioritize simplicity over feature count.
- If two solutions achieve the same outcome, choose the simpler one.
