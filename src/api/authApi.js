import api from "./client";

export const registerUserRequest = (payload) => api.post("/auth/register", payload);
export const loginUserRequest = (payload) => api.post("/auth/login", payload);
export const getMeRequest = () => api.get("/auth/me");

