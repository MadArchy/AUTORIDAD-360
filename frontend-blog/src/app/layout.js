import { DM_Sans, Source_Serif_4 } from "next/font/google";
import "./globals.css";

const display = Source_Serif_4({
  subsets: ["latin"],
  variable: "--font-display",
  weight: ["500", "600", "700"],
});

const body = DM_Sans({
  subsets: ["latin"],
  variable: "--font-body",
  weight: ["400", "500", "600", "700"],
});

export const metadata = {
  title: "AUTORIDAD 360 · Blog",
  description:
    "Inteligencia editorial de Juan Vásquez — análisis Tech & Legal con citación a fuente original.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="es">
      <body className={`${display.variable} ${body.variable}`}>{children}</body>
    </html>
  );
}
