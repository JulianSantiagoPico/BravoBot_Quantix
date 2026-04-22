/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        pb: {
          // Primario
          aqua:        '#0299D8',
          // Secundarios
          navy:        '#001A34',
          'navy-dark': '#0F385A',
          yellow:      '#FFC501',
          purple:      '#4E3D98',
          orange:      '#F29A01',
          red:         '#D8473A',
          green:       '#00B87C',
          gray:        '#4E4E4E',
          // Variantes
          'gray-light':'#F2F6F9',
        },
      },
      fontFamily: {
        heading: ['"Roboto Condensed"', 'sans-serif'],
        body:    ['"Open Sans"',       'sans-serif'],
      },
      animation: {
        'bounce-dot': 'bounceDot 1.4s infinite ease-in-out both',
        'fade-in':    'fadeIn 0.3s ease-out',
        'slide-up':   'slideUp 0.3s ease-out',
      },
      keyframes: {
        bounceDot: {
          '0%, 80%, 100%': { transform: 'scale(0)', opacity: '0.3' },
          '40%':           { transform: 'scale(1)', opacity: '1'   },
        },
        fadeIn:  { from: { opacity: '0' },                          to: { opacity: '1' } },
        slideUp: { from: { opacity: '0', transform: 'translateY(12px)' }, to: { opacity: '1', transform: 'translateY(0)' } },
      },
    },
  },
  plugins: [],
}

