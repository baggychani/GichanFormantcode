/** Binary setting control — project rule: switch with role="switch", not checkbox. */
export function ToggleSwitch({
  label,
  checked,
  onChange,
  disabled = false,
}: {
  label: string;
  checked: boolean;
  onChange: () => void;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      className="setting-switch"
      role="switch"
      aria-checked={checked}
      onClick={onChange}
      disabled={disabled}
    >
      <span>{label}</span>
      <i className={checked ? "is-on" : ""}>
        <b />
      </i>
    </button>
  );
}
