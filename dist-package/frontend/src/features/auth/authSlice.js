import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import { getMeRequest, loginUserRequest, registerUserRequest } from "../../api/authApi";
import { setAuthToken } from "../../api/client";
import { getApiError } from "../../utils/apiError";

const persistedToken = localStorage.getItem("auth_token");

if (persistedToken) {
  setAuthToken(persistedToken);
}

const initialState = {
  user: null,
  token: persistedToken,
  loading: false,
  error: null,
};

export const registerUser = createAsyncThunk("auth/register", async (payload, { rejectWithValue }) => {
  try {
    const response = await registerUserRequest(payload);
    return response.data;
  } catch (error) {
    return rejectWithValue(getApiError(error, "Registration failed"));
  }
});

export const loginUser = createAsyncThunk("auth/login", async (payload, { rejectWithValue }) => {
  try {
    const response = await loginUserRequest(payload);
    return response.data;
  } catch (error) {
    return rejectWithValue(getApiError(error, "Login failed"));
  }
});

export const fetchCurrentUser = createAsyncThunk("auth/me", async (_, { rejectWithValue }) => {
  try {
    const response = await getMeRequest();
    return response.data;
  } catch (error) {
    return rejectWithValue(getApiError(error, "Unable to load profile"));
  }
});

const authSlice = createSlice({
  name: "auth",
  initialState,
  reducers: {
    logout(state) {
      state.user = null;
      state.token = null;
      state.error = null;
      localStorage.removeItem("auth_token");
      setAuthToken(null);
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(registerUser.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(registerUser.fulfilled, (state) => {
        state.loading = false;
      })
      .addCase(registerUser.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      })
      .addCase(loginUser.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(loginUser.fulfilled, (state, action) => {
        state.loading = false;
        state.token = action.payload.access_token;
        state.error = null;
        localStorage.setItem("auth_token", action.payload.access_token);
        setAuthToken(action.payload.access_token);
      })
      .addCase(loginUser.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      })
      .addCase(fetchCurrentUser.fulfilled, (state, action) => {
        state.user = action.payload;
      })
      .addCase(fetchCurrentUser.rejected, (state, action) => {
        state.user = null;
        if (action.payload === "Not authenticated" || action.payload === "Could not validate credentials") {
          state.token = null;
          localStorage.removeItem("auth_token");
          setAuthToken(null);
        }
      });
  },
});

export const { logout } = authSlice.actions;
export default authSlice.reducer;
