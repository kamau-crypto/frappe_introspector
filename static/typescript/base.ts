const nav = document.getElementsByTagName("nav");
const flash_section = document.getElementById("flash_err");
const main_section = document.getElementsByTagName("main");

const navHeight = nav[0].offsetHeight;
if (!flash_section) {
	console.warn(
		"Flash section not found. Please ensure there is an element with id 'flash_err' in the HTML.",
	);
} else {
	flash_section.classList.add(`mt-[${navHeight/4}px]`);
}
main_section![0].classList.add(`mt-[${navHeight + 10}px]`);

const themeToggle = document.getElementById("theme-toggle");
if (!themeToggle) {
	console.warn(
		"Theme toggle button not found. Please ensure there is an element with id 'theme-toggle' in the HTML.",
	);
} else {
	themeToggle.addEventListener("click", () => {
		document.documentElement.classList.toggle("dark");
		if (document.documentElement.classList.contains("dark")) {
			localStorage.theme = "dark";
			document.documentElement.classList.add("dark");
		} else {
			localStorage.theme = "light";
			document.documentElement.classList.remove("dark");
		}
	});

	localStorage.theme === "dark" &&
		document.documentElement.classList.toggle(
			"dark",
			localStorage.theme === "dark" ||
				(!("theme" in localStorage) &&
					window.matchMedia("(prefers-color-scheme: dark)").matches),
		);
}
