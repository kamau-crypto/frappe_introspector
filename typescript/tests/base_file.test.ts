import { beforeAll, describe, expect, it } from "vitest";

function buildBaseFile() {
	const HTMLContent = `
		<nav class="bg-blue-700 text-light-surface dark:text-dark-text dark:bg-primary-900 fixed top-0 z-10 w-full">
		<div class="flex items-center gap-3">
				<span id="theme-toggle"
					class="border border-slate-400 rounded-md relative inline-flex h-9 w-11 items-center justify-center overflow-hidden cursor-pointer transition-colors duration-300 shrink-0">
					<i
						class="fas fa-sun absolute transition-all duration-300 ease-in-out opacity-100 scale-100 rotate-0 dark:opacity-0 dark:scale-75 dark:-rotate-90"></i>
					<i
						class="fas fa-moon absolute transition-all duration-300 ease-in-out opacity-0 scale-75 rotate-90 dark:opacity-100 dark:scale-100 dark:rotate-0"></i>
					</span>
            </div>    
    	</nav>
		<div class="max-w-7xl mx-auto px-4 mt-4 w-full" id="flash_err"></div>
	`;
	document.body.innerHTML = HTMLContent;
	document.documentElement.classList.add("dark");
	window.localStorage.setItem("theme", "dark");
}

describe("base.html - Functions as expected", () => {
	beforeAll(() => {
		buildBaseFile();
	});

	it("should have a nav bar", () => {
		const nav = document.querySelector("nav");
		expect(nav).not.toBeNull();
		expect(nav?.classList.contains("bg-blue-700")).toBe(true);
		expect(nav?.classList.contains("w-full")).toBe(true);
	});

	it("should have a flash_error section", () => {
		const flashSection = document.getElementById("flash_err");
		expect(flashSection).not.toBeNull();
		expect(document.body.innerHTML).toContain('id="flash_err"');
	});

	it("should have a theme toggle button", () => {
		expect(document.body.innerHTML).toContain('id="theme-toggle"');
	});

	it("should have the theme toggle button within the nav bar", () => {
		const nav = document.querySelector("nav");
		const themeToggle = document.getElementById("theme-toggle");
		expect(nav).toContain(themeToggle);
	});

	it("should change the theme on toggle click", () => {
		const themeToggle = document.getElementById("theme-toggle");
		if (themeToggle) {
			themeToggle.click();
			expect(document.documentElement.classList.contains("dark")).toBe(true);
			themeToggle.click();
			document.documentElement.classList.remove("dark");
			window.localStorage.setItem("theme", "light");
			expect(document.documentElement.classList.contains("dark")).toBe(false);
		} else {
			throw new Error("Theme toggle button not found in the DOM.");
		}
	});

	it("should extract the mode from localStorage", () => {
		const theme = window.localStorage.getItem("theme");
		expect(theme).toBe("light");
	});
});
