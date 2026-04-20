import js from "@eslint/js";
import globals from "globals";
import { defineConfig } from "eslint/config";

export default defineConfig([
  {
    files: ["**/*.{js,mjs,cjs,jsx}"],
    plugins: { js },
    extends: ["js/recommended"],
    languageOptions: { 
      globals: globals.browser,
      ecmaVersion: "latest",
      sourceType: "module"
    },
    rules: {
      indent: ["error", 4],
      linebreakStyle: ["error", "unix"],
      quotes: ["error", "single"],
      semi: ["error", "always"],
      "no-unused-vars": "warn",
      "no-console": "off"
    }
  }
]);
