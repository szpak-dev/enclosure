import { sirenRegistry } from "../siren/SirenRegistry";
import { LanguageCollection, LanguageDetail } from "./LanguageViews";

class LanguageRendererRegistration {
  private registered = false;
  register(): void {
    if (this.registered) return;
    sirenRegistry.collections.register("language", LanguageCollection);
    sirenRegistry.entities.register("language", LanguageDetail);
    this.registered = true;
  }
}

const registration = new LanguageRendererRegistration();
export function registerLanguageRenderers(): void {
  registration.register();
}
