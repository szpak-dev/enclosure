import type { SirenActionFormProps } from "../siren/SirenActionForm";
import { ProjectActions } from "./ProjectActions";

export function OperatingContractAction({
  action,
  values,
}: SirenActionFormProps) {
  return (
    <ProjectActions
      actions={[action]}
      dangerNames={[]}
      omitNames={[]}
      onRefresh={() => {}}
      primaryName="create_operating_contract"
      values={values ? values : {}}
    />
  );
}
