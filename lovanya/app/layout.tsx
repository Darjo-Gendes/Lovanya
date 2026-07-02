import type { Metadata, Viewport } from "next";
import {
  Playfair_Display,
  Poppins,
  Parisienne,
  Dancing_Script,
} from "next/font/google";
import "./globals.css";
import AppShell from "@/components/AppShell";

const playfair = Playfair_Display({
  variable: "--font-playfair",
  subsets: ["latin"],
});

const dancing = Dancing_Script({
  variable: "--font-dancing",
  subsets: ["latin"],
  weight: ["600", "700"],
});

const poppins = Poppins({
  variable: "--font-poppins",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

const parisienne = Parisienne({
  variable: "--font-parisienne",
  subsets: ["latin"],
  weight: "400",
});

export const metadata: Metadata = {
  title: "Lovanya — Your Best Friend in Fashion",
  description:
    "A premium fashion companion that helps you decide what to wear, organize your wardrobe, and feel confident every day.",
  manifest: "/manifest.webmanifest",
  icons: { icon: "/icon.svg", apple: "/icon.svg" },
};

export const viewport: Viewport = {
  themeColor: "#faeded",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${playfair.variable} ${poppins.variable} ${parisienne.variable} ${dancing.variable} h-full antialiased`}
    >
      <body className="min-h-dvh">
        <div className="app-wash" />
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
