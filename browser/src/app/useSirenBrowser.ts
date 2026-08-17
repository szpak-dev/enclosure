import type { Action, Entity, Target } from "@siren-js/client";
import { useCallback, useEffect, useRef, useState } from "react";
import type { SirenClient } from "../client/SirenClient";

type BrowserEntity = Entity<object>;

function error(reason: unknown, fallback: string): Error {
  return reason instanceof Error ? reason : new Error(fallback);
}

function href(target: Target): string {
  return (typeof target === "string" ? target : target.href).toString();
}

function sameTarget(left: Target, right: Target): boolean {
  return (
    new URL(href(left), window.location.origin).href ===
    new URL(href(right), window.location.origin).href
  );
}

export function useSirenBrowser(client: SirenClient, rootTarget: Target) {
  const [root, setRoot] = useState<BrowserEntity | null>(null);
  const [entity, setEntity] = useState<BrowserEntity | null>(null);
  const [rootError, setRootError] = useState<Error | null>(null);
  const [resourceError, setResourceError] = useState<Error | null>(null);
  const [isRootLoading, setIsRootLoading] = useState(true);
  const [isResourceLoading, setIsResourceLoading] = useState(false);
  const [target, setTarget] = useState<Target>(
    () => window.location.hash.slice(1) || rootTarget,
  );
  const rootRequest = useRef<Promise<BrowserEntity> | null>(null);
  const targetIsRoot = sameTarget(target, rootTarget);

  const loadRoot = useCallback(
    async (refresh = false) => {
      if (refresh) rootRequest.current = null;
      setRootError(null);
      setIsRootLoading(true);
      try {
        const request = rootRequest.current ?? client.get(rootTarget);
        rootRequest.current = request;
        setRoot(await request);
      } catch (reason) {
        rootRequest.current = null;
        setRootError(error(reason, "Unable to load the Siren entry point."));
      } finally {
        setIsRootLoading(false);
      }
    },
    [client, rootTarget],
  );

  const load = useCallback(
    (nextTarget: Target) => client.get(nextTarget),
    [client],
  );

  const loadResource = useCallback(
    async (nextTarget: Target) => {
      setResourceError(null);
      setIsResourceLoading(true);
      try {
        setEntity(await load(nextTarget));
      } catch (reason) {
        setResourceError(error(reason, "Unable to load the Siren resource."));
      } finally {
        setIsResourceLoading(false);
      }
    },
    [load],
  );

  useEffect(() => {
    void loadRoot();
  }, [loadRoot]);

  useEffect(() => {
    if (targetIsRoot) {
      setResourceError(null);
      setEntity(root);
    }
  }, [root, targetIsRoot]);

  useEffect(() => {
    if (!targetIsRoot) void loadResource(target);
  }, [loadResource, target, targetIsRoot]);

  useEffect(() => {
    const onHashChange = () =>
      setTarget(window.location.hash.slice(1) || rootTarget);
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, [rootTarget]);

  const follow = (nextTarget: Target) => {
    const nextHref = href(nextTarget);
    window.location.hash = nextHref;
    setTarget(nextHref);
  };

  const retry = () => {
    if (targetIsRoot) {
      void loadRoot(true);
    } else {
      void loadResource(target);
    }
  };

  const submit = async (action: Action, values: Record<string, unknown>) => {
    setResourceError(null);
    try {
      const response = await client.execute(action, values);
      if (response) {
        setEntity(response);
      } else if (targetIsRoot) {
        await loadRoot(true);
      } else {
        await loadResource(target);
      }
    } catch (reason) {
      const submissionError = error(
        reason,
        "Unable to submit the Siren action.",
      );
      throw submissionError;
    }
  };

  return {
    entity,
    error: targetIsRoot ? rootError : resourceError,
    follow,
    isLoading: targetIsRoot ? isRootLoading : isResourceLoading,
    load,
    retry,
    retryRoot: () => void loadRoot(true),
    root,
    rootError: targetIsRoot ? null : rootError,
    submit,
    target,
  };
}
