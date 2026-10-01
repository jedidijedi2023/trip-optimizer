import type { Metadata } from 'next';
import './globals.css';
export const metadata: Metadata = {title:'Global Travel Optimizer — конструктор отдыха',description:'Сравнение полной стоимости семейного отдыха, визовых условий и маршрутов через альтернативные аэропорты.'};
export default function RootLayout({children}:{children:React.ReactNode}) {return <html lang="ru"><body>{children}</body></html>}
