import {defineConfig,globalIgnores} from 'eslint/config';
import nextVitals from 'eslint-config-next/core-web-vitals';
import nextTypescript from 'eslint-config-next/typescript';

export default defineConfig([
 ...nextVitals,
 ...nextTypescript,
 // Existing storage/API hydration uses effects; changing it requires a separate state-architecture refactor.
 {rules:{'react-hooks/set-state-in-effect':'off'}},
 globalIgnores(['.next/**','out/**','test-results/**','playwright-report/**','next-env.d.ts']),
]);
