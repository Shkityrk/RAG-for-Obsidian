import { requestUrl } from "obsidian";

import type {
	GatewayFileEventPayload,
	GatewayLoginRequest,
	GatewayLoginResponse,
} from "../types";

interface HttpErrorPayload {
	detail?: string;
	message?: string;
}

export class GatewayClient {
	constructor(private readonly getBaseUrl: () => string) {}

	async login(payload: GatewayLoginRequest): Promise<GatewayLoginResponse> {
		return this.postJson<GatewayLoginResponse>("/api/auth/login", payload);
	}

	async sendFileEvent(token: string, payload: GatewayFileEventPayload): Promise<void> {
		await this.postJson<unknown>("/api/files/events", payload, token);
	}

	private async postJson<TResponse>(
		path: string,
		payload: object,
		token?: string,
	): Promise<TResponse> {
		const headers: Record<string, string> = {
			"Content-Type": "application/json",
		};
		if (token) {
			headers.Authorization = `Bearer ${token}`;
		}

		const baseUrl = this.getBaseUrl().replace(/\/+$/u, "");
		const fullUrl = `${baseUrl}${path}`;

		try {
			const response = await requestUrl({
				url: fullUrl,
				method: "POST",
				headers,
				body: JSON.stringify(payload),
			});

			if (response.status >= 400) {
				let errorBody: HttpErrorPayload | null = null;
				try {
					errorBody = response.json as HttpErrorPayload | null;
				} catch {
					// Если не JSON, используем text
				}
				const detail = errorBody?.detail ?? errorBody?.message ?? response.text ?? "Unknown error";
				
				if (response.status === 401) {
					throw new Error(`Неверное имя пользователя или пароль (${response.status})`);
				}
				if (response.status === 403) {
					throw new Error(`Доступ запрещен (${response.status}): ${detail}`);
				}
				if (response.status === 404) {
					throw new Error(`Эндпоинт не найден: ${path} (${response.status})`);
				}
				if (response.status === 400) {
					throw new Error(`Ошибка валидации (${response.status}): ${detail}`);
				}
				if (response.status >= 500) {
					throw new Error(`Ошибка сервера (${response.status}): ${detail}`);
				}
				throw new Error(`${detail} (${response.status})`);
			}
			return response.json as TResponse;
		} catch (error: unknown) {
			if (error instanceof Error) {
				throw error;
			}
			throw new Error(`Network error: не удалось подключиться к ${baseUrl}`);
		}
	}
}

