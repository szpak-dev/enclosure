import type { Action } from "@siren-js/client";
import { createContext, useContext, type ReactNode } from "react";
import type { ActionExecutionResult } from "../../app/useSirenBrowser";

export type SirenActionExecutor = (
  action: Action,
  values: Record<string, unknown>,
) => Promise<ActionExecutionResult>;

type SirenActionExecutionState =
  { kind: "available"; execute: SirenActionExecutor } | { kind: "unavailable" };

const SirenActionExecutionContext = createContext<SirenActionExecutionState>({
  kind: "unavailable",
});

export type SirenActionExecutionProviderProps = {
  children: ReactNode;
  execute: SirenActionExecutor;
};

export function SirenActionExecutionProvider({
  children,
  execute,
}: SirenActionExecutionProviderProps): ReactNode {
  return (
    <SirenActionExecutionContext.Provider
      value={{ kind: "available", execute }}
    >
      {children}
    </SirenActionExecutionContext.Provider>
  );
}

export function useSirenActionExecution(): SirenActionExecutionState {
  return useContext(SirenActionExecutionContext);
}
