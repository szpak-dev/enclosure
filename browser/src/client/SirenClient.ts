import {
  follow,
  parse,
  submit,
  type Action,
  type Entity,
  type Href,
  type Target,
} from "@siren-js/client";
import { applyActionValues } from "./ActionValues";
import { sirenResponseError } from "./SirenError";

export { SirenResponseError } from "./SirenError";

export const SIREN_ACCEPT = "application/vnd.siren+json, application/json";
export const SIREN_ACTOR_HEADERS = {
  "X-Actor-Id": "browser-user",
  "X-Actor-Type": "user",
};

export type SirenClientOptions = {
  baseUrl?: Href;
  headers?: HeadersInit;
};

export type SirenRequestOptions = {
  headers?: HeadersInit;
  signal?: AbortSignal;
};

export class SirenClient {
  private readonly baseUrl: Href;
  private readonly headers: Headers;

  constructor({
    baseUrl = window.location.origin,
    headers,
  }: SirenClientOptions = {}) {
    this.baseUrl = baseUrl;
    this.headers = new Headers(SIREN_ACTOR_HEADERS);
    new Headers(headers).forEach((value, name) =>
      this.headers.set(name, value),
    );
  }

  async get<T extends object = object>(
    target: Target,
    options: SirenRequestOptions = {},
  ): Promise<Entity<T>> {
    const response = await follow(target, {
      baseUrl: this.baseUrl,
      requestInit: this.requestInit(options),
    });
    return this.entity<T>(response);
  }

  async execute<T extends object = object>(
    action: Action,
    values: Record<string, unknown> = {},
    options: SirenRequestOptions = {},
  ): Promise<Entity<T> | null> {
    applyActionValues(action, values);
    const response = await submit(action, {
      baseUrl: this.baseUrl,
      requestInit: this.requestInit(options),
    });

    if (response.status === 204) {
      return null;
    }

    return this.entity<T>(
      response,
      action.fields.map((field) => field.name),
    );
  }

  private async entity<T extends object>(
    response: Response,
    fields: string[] = [],
  ): Promise<Entity<T>> {
    if (!response.ok) {
      throw await sirenResponseError(response, fields);
    }

    return parse<T>(response);
  }

  private requestInit({ headers, signal }: SirenRequestOptions): RequestInit {
    const requestHeaders = new Headers(this.headers);
    new Headers(headers).forEach((value, name) =>
      requestHeaders.set(name, value),
    );
    requestHeaders.set("Accept", requestHeaders.get("Accept") ?? SIREN_ACCEPT);
    return signal
      ? { headers: requestHeaders, signal }
      : { headers: requestHeaders };
  }
}
