import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";

type OpenAIModelInfo = {
	id: string;
	name?: string;
	context_window?: number;
	max_tokens?: number;
	input_modalities?: string[];
	modalities?: string[];
};

type OpenAIModelsResponse =
	| {
		data?: OpenAIModelInfo[];
	}
	| OpenAIModelInfo[];

const PROVIDER_NAME = "op-rtd-07";
const BASE_URL = "http://op-rtd-07:8080/v1";
const API_KEY = "test_api_key_that_no_one_would_guess";

function normalizeBaseUrl(url: string): string {
	return url.replace(/\/$/, "");
}

function unwrapModels(payload: OpenAIModelsResponse): OpenAIModelInfo[] {
	if (Array.isArray(payload)) {
		return payload;
	}

	return payload.data ?? [];
}

function inferInput(model: OpenAIModelInfo): Array<"text" | "image"> {
	const modalities = model.input_modalities ?? model.modalities ?? [];
	return modalities.includes("image") ? ["text", "image"] : ["text"];
}

async function discoverModels(baseUrl: string): Promise<OpenAIModelInfo[]> {
	const response = await fetch(`${baseUrl}/models`, {
		headers: {
			Authorization: `Bearer ${API_KEY}`,
			Accept: "application/json",
		},
	});

	if (!response.ok) {
		const body = await response.text();
		throw new Error(`Failed to discover models from ${baseUrl}/models: ${response.status} ${body}`);
	}

	const payload = (await response.json()) as OpenAIModelsResponse;
	const discoveredModels = unwrapModels(payload);

	if (discoveredModels.length === 0) {
		throw new Error(`No models discovered from ${baseUrl}/models`);
	}

	return discoveredModels;
}

function registerBaseProvider(pi: ExtensionAPI, baseUrl: string) {
	pi.registerProvider(PROVIDER_NAME, {
		baseUrl,
		apiKey: API_KEY,
		authHeader: true,
		api: "openai-completions",
		compat: {
			supportsDeveloperRole: false,
			supportsReasoningEffort: false,
			maxTokensField: "max_tokens",
		},
	});
}

async function refreshDiscoveredModels(pi: ExtensionAPI, baseUrl: string) {
	try {
		const discoveredModels = await discoverModels(baseUrl);

		pi.registerProvider(PROVIDER_NAME, {
			baseUrl,
			apiKey: API_KEY,
			authHeader: true,
			api: "openai-completions",
			compat: {
				supportsDeveloperRole: false,
				supportsReasoningEffort: false,
				maxTokensField: "max_tokens",
			},
			models: discoveredModels.map((model) => ({
				id: model.id,
				name: model.name ?? model.id,
				reasoning: false,
				input: inferInput(model),
				cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 },
				contextWindow: model.context_window ?? 128000,
				maxTokens: model.max_tokens ?? 16384,
			})),
		});
	} catch (error) {
		console.error(`[${PROVIDER_NAME}] model discovery failed:`, error);
	}
}

export default function (pi: ExtensionAPI) {
	const baseUrl = normalizeBaseUrl(BASE_URL);
	registerBaseProvider(pi, baseUrl);
	void refreshDiscoveredModels(pi, baseUrl);
}
