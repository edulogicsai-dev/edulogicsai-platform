/**
 * Compile-time-only assertions (AC2, AC4). Not executed — checked by
 * `tsc --noEmit`. A `@ts-expect-error` that doesn't materialize is itself
 * a type error, so this file fails to type-check if the constraint breaks.
 */
import type { DomainConfig, ThemeVars } from './domain-config';

// AC2: omitting a required DomainConfig field must fail to type-check.
// @ts-expect-error - missing name, subdomain, agents, contentIndex, evalRubric, theme, escalationRules
const _incompleteDomainConfig: DomainConfig = {
  id: 'incomplete',
};

// AC4: a non-CSS-custom-property field on ThemeVars must fail to type-check.
const _invalidTheme: ThemeVars = {
  '--color-primary': '#000',
  // @ts-expect-error - "componentOverride" is not a CSS custom property name
  componentOverride: 'not-allowed',
};

// Sanity check: a fully valid DomainConfig type-checks with no errors.
const _validDomainConfig: DomainConfig = {
  id: 'valid',
  name: 'Valid Domain',
  subdomain: 'app.valid.co',
  agents: [],
  contentIndex: 'valid_content',
  evalRubric: { criteria: [] },
  theme: { '--color-primary': '#fff' },
  escalationRules: [],
};

void _incompleteDomainConfig;
void _invalidTheme;
void _validDomainConfig;
