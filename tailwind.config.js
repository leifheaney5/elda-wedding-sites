module.exports = {
  content: [
    "./app/templates/**/*.html",
    "./app/static/js/**/*.js",
  ],
  theme: {
    extend: {
      colors: {
        "bbb-sand": "#EFE8E1",
        "bbb-cream": "#F7F4F1",
        "bbb-tan": "#DAD1C8",
        "bbb-blush": "#EADCDB",
        "bbb-teal": "#88A096",
        "bbb-teal-dark": "#6F8780",
        "bbb-navy": "#273445",
        "bbb-coral": "#C9928B",
        "bbb-gold": "#B8A48E",
        "bbb-text": "#3F3F42",
      },
      fontFamily: {
        serif: ["Cormorant Garamond", "Georgia", "serif"],
        sans: ["Manrope", "Inter", "sans-serif"],
        script: ["Great Vibes", "cursive"],
      },
    },
  },
  plugins: [],
};
