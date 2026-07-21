export function SettingsSwitch({
  checked,
  onChange,
  disabled = false,
}: {
  checked: boolean;
  onChange: () => void;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      className="settings-switch-control"
      role="switch"
      aria-checked={checked}
      onClick={onChange}
      disabled={disabled}
      aria-label={checked ? "켜짐" : "꺼짐"}
    >
      <i className={checked ? "is-on" : ""}>
        <b />
      </i>
    </button>
  );
}
