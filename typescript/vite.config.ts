import type { UserConfig } from "vite";

export default {
	build: {
		outDir: "../static/typescript",
		assetsDir: "",
		minify: "oxc",
		watch: {
			include: "src/**/*",
		},
		emptyOutDir: false,
		rollupOptions: {
			input: {
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
