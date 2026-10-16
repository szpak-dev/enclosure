import { sirenRegistry } from "../siren/SirenRegistry";
import {
  ArchitectureConfigurationCollection,
  ArchitectureConfigurationEntity,
} from "./ArchitectureConfiguration";
import {
  GuidanceRelationshipCollection,
  GuidanceScopeCollection,
} from "./GuidanceCollections";
import { OperatingContractAction } from "./OperatingContractAction";
import { ProjectCollection } from "./ProjectCollection";
import { ProjectEntity } from "./ProjectEntity";
import { ProjectArtifactEntity } from "./ProjectArtifactEntity";
import { WorkspaceCollection } from "./WorkspaceCollection";
import { WorkspaceEntity } from "./WorkspaceEntity";

let registered = false;

export function registerProjectRenderers(): void {
  if (registered) return;
  sirenRegistry.actions.set(
    "create_operating_contract",
    OperatingContractAction,
  );
  sirenRegistry.collections.register("project", ProjectCollection);
  sirenRegistry.collections.register("workspace", WorkspaceCollection);
  sirenRegistry.collections.register(
    "architecture-configuration",
    ArchitectureConfigurationCollection,
  );
  sirenRegistry.collections.register("guidance-scope", GuidanceScopeCollection);
  sirenRegistry.collections.register(
    "guidance-relationship",
    GuidanceRelationshipCollection,
  );
  sirenRegistry.entities.register("project", ProjectEntity);
  sirenRegistry.entities.register("workspace", WorkspaceEntity);
  sirenRegistry.entities.register(
    "architecture-configuration",
    ArchitectureConfigurationEntity,
  );
  sirenRegistry.entities.register("operating-contract", ProjectArtifactEntity);
  sirenRegistry.entities.register("revision", ProjectArtifactEntity);
  sirenRegistry.entities.register(
    "architecture-contract-publication",
    ProjectArtifactEntity,
  );
  sirenRegistry.entities.register("comparison", ProjectArtifactEntity);
  registered = true;
}
