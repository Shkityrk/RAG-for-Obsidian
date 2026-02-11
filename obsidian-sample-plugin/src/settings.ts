import { App, PluginSettingTab, Setting } from "obsidian";

import VaultGatewaySyncPlugin from "./main";

export interface PluginSettings {
	gatewayUrl: string;
	username: string;
	password: string;
	accessToken: string;
	syncEnabled: boolean;
	autoLoginOnLoad: boolean;
	debounceMs: number;
}

export const DEFAULT_SETTINGS: PluginSettings = {
	gatewayUrl: "http://127.0.0.1:8001",
	username: "",
	password: "",
	accessToken: "",
	syncEnabled: true,
	autoLoginOnLoad: false,
	debounceMs: 800,
};

export class SyncSettingTab extends PluginSettingTab {
	plugin: VaultGatewaySyncPlugin;

	constructor(app: App, plugin: VaultGatewaySyncPlugin) {
		super(app, plugin);
		this.plugin = plugin;
	}

	display(): void {
		const { containerEl } = this;
		containerEl.empty();

		new Setting(containerEl)
			.setName("Gateway URL")
			.setDesc("URL gateway-сервиса, через который плагин общается с backend")
			.addText((text) =>
				text
					.setPlaceholder("http://127.0.0.1:8001")
					.setValue(this.plugin.settings.gatewayUrl)
					.onChange(async (value) => {
						this.plugin.settings.gatewayUrl = value.trim();
						await this.plugin.saveSettings();
					}),
			);

		new Setting(containerEl)
			.setName("Username")
			.setDesc("Логин для авторизации в auth через gateway")
			.addText((text) =>
				text.setValue(this.plugin.settings.username).onChange(async (value) => {
					this.plugin.settings.username = value.trim();
					await this.plugin.saveSettings();
				}),
			);

		new Setting(containerEl)
			.setName("Password")
			.setDesc("Пароль пользователя")
			.addText((text) =>
				text
					.setPlaceholder("Password")
					.setValue(this.plugin.settings.password)
					.onChange(async (value) => {
						this.plugin.settings.password = value;
						this.plugin.settings.accessToken = "";
						await this.plugin.saveSettings();
					}),
			);

		new Setting(containerEl)
			.setName("Enable sync")
			.setDesc("Включить отправку событий create/modify/delete/rename в gateway")
			.addToggle((toggle) =>
				toggle.setValue(this.plugin.settings.syncEnabled).onChange(async (value) => {
					this.plugin.settings.syncEnabled = value;
					await this.plugin.saveSettings();
				}),
			);

		new Setting(containerEl)
			.setName("Auto login on load")
			.setDesc("Пробовать логиниться автоматически при старте плагина")
			.addToggle((toggle) =>
				toggle.setValue(this.plugin.settings.autoLoginOnLoad).onChange(async (value) => {
					this.plugin.settings.autoLoginOnLoad = value;
					await this.plugin.saveSettings();
				}),
			);

		new Setting(containerEl)
			.setName("Debounce (ms)")
			.setDesc("Задержка перед отправкой события, чтобы сгладить серию микросохранений")
			.addText((text) =>
				text
					.setPlaceholder("800")
					.setValue(String(this.plugin.settings.debounceMs))
					.onChange(async (value) => {
						const parsed = Number.parseInt(value, 10);
						if (!Number.isFinite(parsed) || parsed < 0) {
							return;
						}
						this.plugin.settings.debounceMs = parsed;
						await this.plugin.saveSettings();
					}),
			);
	}
}
