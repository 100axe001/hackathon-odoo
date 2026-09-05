import js from "@eslint/js";
import globals from "globals";
import react from "eslint-plugin-react";
import reactHooks from "eslint-plugin-react-hooks";

export default [
  { ignores: ["dist/**", "node_modules/**", "scripts/shots/**"] },
  js.configs.recommended,
  {
    // Tooling that runs in Node. Browser globals are included too because the
    // body of a page.evaluate() callback executes in the page, not in Node.
    files: ["scripts/**/*.mjs", "*.config.js"],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "module",
      globals: { ...globals.node, ...globals.browser },
    },
  },
  {
    files: ["**/*.{js,jsx}"],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "module",
      globals: { ...globals.browser },
      parserOptions: { ecmaFeatures: { jsx: true } },
    },
    plugins: { react, "react-hooks": reactHooks },
    settings: { react: { version: "detect" } },
    rules: {
      // Only rules-of-hooks. The v6 preset also ships exhaustive-deps plus
      // experimental purity / set-state-in-effect rules, which fire on patterns
      // this codebase already uses deliberately (a temp id from Date.now() in an
      // event handler, the mount animation in Transition). PictoPy likewise runs
      // with exhaustive-deps off.
      "react-hooks/rules-of-hooks": "error",

      // Without a type checker, no-undef is the main safety net. It catches a
      // hook used but never imported - the exact bug that shipped a green build
      // when the router conversion missed a useNavigate().
      "no-undef": "error",
      "no-unused-vars": ["error", { argsIgnorePattern: "^_" }],

      // JSX counts as usage, otherwise every imported component looks unused.
      "react/jsx-uses-vars": "error",
      "react/jsx-uses-react": "off",

      // no-undef does NOT inspect JSX element names - <Foo /> and
      // <React.Fragment> are JSX(Member)Expressions, not identifier references.
      // Without this rule a missing component import ships silently, which is
      // exactly how Stepper reached a green build calling undefined React.
      "react/jsx-no-undef": ["error", { allowGlobals: false }],

      // See AGENTS.md: incomplete work goes in README, not in a marker nobody
      // finds again.
      "no-warning-comments": [
        "error",
        { terms: ["todo", "fixme"], location: "anywhere" },
      ],
    },
  },
];
