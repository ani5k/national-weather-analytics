/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        void: '#FFFFFF',
        panel: 'oklch(95.1% 0.026 236.824)',
        'panel-raised': 'oklch(91% 0.032 236.824)',
        storm: 'oklch(83% 0.03 236.824)',
        'text-primary': 'oklch(27% 0.03 236.824)',
        'text-muted': 'oklch(50% 0.02 236.824)',
        rain: '#2563EB',
        verified: '#0891B2',
        alert: '#EA580C',
        warn: '#B45309',
        thunder: '#7C3AED',
        // Softer fill variants for map zones / chart areas (same hues, lower saturation on white)
        'rain-soft': '#93C5FD',
        'alert-soft': '#FDBA8C',
        'thunder-soft': '#C4B5FD',
      },
      fontFamily: {
        display: ['"Space Grotesk"', 'sans-serif'],
        body: ['Inter', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      boxShadow: {
        glow: '0 1px 2px rgba(30,41,59,0.05), 0 6px 16px rgba(30,41,59,0.06)',
      },
    },
  },
  plugins: [],
}
