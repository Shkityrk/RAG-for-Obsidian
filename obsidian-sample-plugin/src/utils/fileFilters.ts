const TEMP_FILE_RE = /(^|\/)(~\$|\.~|tmp-|temp-)|\.(tmp|temp|swp|swo|bak|crdownload)$/iu;
const BINARY_EXTENSIONS = new Set<string>([
	"png",
	"jpg",
	"jpeg",
	"gif",
	"webp",
	"bmp",
	"ico",
	"pdf",
	"zip",
	"7z",
	"rar",
	"gz",
	"mp3",
	"wav",
	"ogg",
	"mp4",
	"avi",
	"mov",
	"exe",
	"dll",
	"bin",
]);

export function isIgnoredVaultPath(path: string, configDir: string): boolean {
	const normalized = path.replace(/\\/gu, "/");
	const normalizedConfigDir = configDir.replace(/\\/gu, "/").replace(/^\/+/u, "").replace(/\/+$/u, "");
	return (
		normalized.startsWith(`${normalizedConfigDir}/`) ||
		normalized.includes(`/${normalizedConfigDir}/`)
	);
}

export function isTempPath(path: string): boolean {
	return TEMP_FILE_RE.test(path.toLowerCase());
}

export function isMarkdownPath(path: string): boolean {
	return path.toLowerCase().endsWith(".md");
}

export function isBinaryPath(path: string): boolean {
	const ext = path.split(".").pop()?.toLowerCase() ?? "";
	return ext.length > 0 && BINARY_EXTENSIONS.has(ext);
}

export function shouldSkipPath(path: string, configDir: string): boolean {
	return isIgnoredVaultPath(path, configDir) || isTempPath(path) || isBinaryPath(path);
}

