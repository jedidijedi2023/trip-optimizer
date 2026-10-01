import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Global Travel Optimizer — конструктор отдыха',
  description:
    'Сравнение полной стоимости семейного отдыха, визовых условий и маршрутов через альтернативные аэропорты.',
};

const travelpayoutsDriveAttributes = {
  nowprocket: '',
  'data-noptimize': '1',
  'data-cfasync': 'false',
  'data-wpfc-render': 'false',
  'seraph-accel-crit': '1',
  'data-no-defer': '1',
  'data-cmp-ab': '2',
};

const travelpayoutsDriveCode = `(function () {
  var script = document.createElement("script");
  script.async = 1;
  script.setAttribute("data-cmp-ab","2");
  script.src = 'https://emrldtp.cc/NTgwMDEz.js?t=580013';
  document.head.appendChild(script);
})();`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ru">
      <head>
        <script
          {...travelpayoutsDriveAttributes}
          dangerouslySetInnerHTML={{ __html: travelpayoutsDriveCode }}
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
