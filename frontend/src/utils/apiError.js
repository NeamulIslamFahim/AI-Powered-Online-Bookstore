export function getApiError(error, fallbackMessage) {
  if (error?.response?.data?.error) {
    if (Array.isArray(error.response.data.error)) {
      return error.response.data.error
        .map((entry) => {
          const field = Array.isArray(entry?.loc) ? entry.loc.at(-1) : null;
          const label = typeof field === "string" ? field.replace(/_/g, " ") : "field";
          return `${label}: ${entry?.msg || "Invalid value"}`;
        })
        .join(". ");
    }
    return error.response.data.error;
  }

  if (error?.response?.data?.detail) {
    return error.response.data.detail;
  }

  if (error?.message === "Network Error") {
    return "Cannot reach the backend server";
  }

  return fallbackMessage;
}
