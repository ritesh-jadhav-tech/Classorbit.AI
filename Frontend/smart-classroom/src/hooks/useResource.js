import { useEffect, useState } from "react";

export function useResource(loader, fallback = []) {
  const [data, setData] = useState(fallback);
  const [status, setStatus] = useState("loading");
  const [error, setError] = useState("");

  useEffect(() => {
    let isMounted = true;

    loader()
      .then((payload) => {
        if (!isMounted) return;
        setData(payload);
        setStatus("success");
      })
      .catch((resourceError) => {
        if (!isMounted) return;
        setError(resourceError?.message || "Unable to load this section.");
        setStatus("error");
      });

    return () => {
      isMounted = false;
    };
  }, [loader]);

  return {
    data,
    setData,
    isLoading: status === "loading",
    isError: status === "error",
    error,
  };
}
