const STATUS_CLASSES = {
  healthy: "bg-status-healthy",
  unhealthy: "bg-status-unhealthy",
  unknown: "bg-status-unknown",
};

export default function StatusDot({ status = "unknown" }) {
  return (
    <span
      className={`inline-block h-2.5 w-2.5 rounded-full ${STATUS_CLASSES[status] || STATUS_CLASSES.unknown}`}
    />
  );
}
