import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        paper: 'var(--paper)',
        sheet: {
          DEFAULT: 'var(--sheet)',
          glass: 'var(--sheet-glass)',
          card: 'var(--sheet-card)',
        },
        ink: {
          DEFAULT: 'var(--ink)',
          soft: 'var(--ink-soft)',
        },
        rule: {
          DEFAULT: 'var(--rule)',
          bright: 'var(--rule-bright)',
        },
        verdigris: {
          DEFAULT: 'var(--verdigris)',
          hover: 'var(--verdigris-hover)',
        },
        oxide: 'var(--oxide)',
        cobalt: 'var(--cobalt)',
        amber: 'var(--amber)',
        moss: 'var(--moss)',
      },
      fontFamily: {
        sans: ['var(--font-sans)', 'sans-serif'],
        serif: ['var(--font-serif)', 'serif'],
        mono: ['var(--font-mono)', 'monospace'],
      },
      borderRadius: {
        DEFAULT: '6px',
        sm: '4px',
        md: '8px',
        lg: '12px',
        xl: '16px',
        '2xl': '20px',
      },
    },
  },
  plugins: [],
};

export default config;
