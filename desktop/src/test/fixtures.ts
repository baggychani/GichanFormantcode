import type { ApplicationState, HealthStatus } from "../../ipc/protocol";

type ApplicationStateOverrides = Omit<
  Partial<ApplicationState>,
  "analysis" | "plot_session" | "capabilities"
> & {
  analysis?: Partial<ApplicationState["analysis"]>;
  plot_session?: Partial<ApplicationState["plot_session"]>;
  capabilities?: Partial<ApplicationState["capabilities"]>;
};

export function createApplicationState(
  overrides: ApplicationStateOverrides = {},
): ApplicationState {
  const base: ApplicationState = {
    analysis: {
      type: "f1_f2",
      f1_scale: "linear",
      f2_scale: "bark",
      origin: "upper_right",
      use_bark_units: false,
      outlier_mode: null,
      outlier_scope: null,
      normalization: null,
    },
    current_index: 0,
    current_vowels: [],
    design_defaults: {},
    plot_session: {
      revision: 0,
      active: false,
      current_idx: 0,
      ranges: {},
      sigma: "2",
      show_ellipse: true,
      design_settings: {},
      vowel_filter_state_by_file: {},
      layer_design_overrides_by_file: {},
      layer_locked_vowels_by_file: {},
      layer_order_by_file: {},
      draw_objects_by_file: {},
    },
    sources: [],
    capabilities: {
      can_plot: false,
      can_compare: false,
      can_save_project: false,
    },
  };

  return {
    ...base,
    ...overrides,
    analysis: { ...base.analysis, ...overrides.analysis },
    plot_session: { ...base.plot_session, ...overrides.plot_session },
    capabilities: { ...base.capabilities, ...overrides.capabilities },
  };
}

export function createHealthStatus(
  overrides: Partial<HealthStatus> = {},
): HealthStatus {
  return {
    ok: true,
    pid: 42,
    uptime_ms: 1,
    version: "3.0.0",
    protocol_version: 1,
    headless: false,
    commands: [],
    ...overrides,
  };
}

export function createDeferred<T>() {
  let resolve!: (value: T | PromiseLike<T>) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
}
