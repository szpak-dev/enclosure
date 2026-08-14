import type { ComponentType } from "react";
import type { SirenActionFormProps } from "./SirenActionForm";
import { SirenEntityRendererRegistry } from "./SirenEntityRendererRegistry";
import type { SirenFieldProps } from "./SirenField";

export const sirenRegistry = {
  actions: new Map<string, ComponentType<SirenActionFormProps>>(),
  entities: new SirenEntityRendererRegistry(),
  fields: new Map<string, ComponentType<SirenFieldProps>>(),
};
