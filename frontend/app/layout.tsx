import "./globals.css";
import type { ReactNode } from "react";

export const metadata = { title: "ENK AI VIDEO", description: "Создавайте видео по тексту и фото" };

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="ru">
      <body>{children}</body>
    </html>
  );
}
