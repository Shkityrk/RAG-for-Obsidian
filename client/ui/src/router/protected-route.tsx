import { Navigate } from "react-router-dom";
import { isAuthenticated } from "../utils/auth";
import type { ReactNode } from "react";

interface ProtectedRouteProps {
    children: ReactNode;
}

export const ProtectedRoute = ({ children }: ProtectedRouteProps) => {
    if (!isAuthenticated()) {
        return <Navigate to="/auth" replace />;
    }
    return <>{children}</>;
};
