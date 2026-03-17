import tailwindcss from "@tailwindcss/vite";
import type { UserConfig } from "vite";

export default {
	plugins: [tailwindcss()],
	build: {
		outDir: "../static/typescript",
		assetsDir: "",
		minify: "oxc",
		watch: {
			include: "src/**/*",
		},
		emptyOutDir: false,
		rollupOptions: {
			output: {
				entryFileNames: "[name].js", // chat.js, base.js, etc.
				assetFileNames: "[name][extname]", // style.css
			},
			input: {
				style: "src/style.css",
				main: "src/main.ts",
				chat: "src/chat.ts",
				prompt: "src/prompt.ts",
				client_error: "src/client_error.ts",
				base: "src/base.ts",
			},
		},
	},

	publicDir: false,
} satisfies UserConfig;
