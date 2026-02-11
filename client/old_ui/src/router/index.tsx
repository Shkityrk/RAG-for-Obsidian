import {createBrowserRouter, Navigate} from "react-router-dom";
import {Page404} from "../pages/404";
import {ChatPage} from "../pages/chat";
import {SettingsPage} from "../pages/settings";
import {IndexPage} from "../pages/index";
import {AuthPage} from "../pages/auth";
import {VaultsPage} from "../pages/vaults";
import {isAuthenticated} from "../utils/auth";

// Компонент для защиты маршрутов
const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
    if (!isAuthenticated()) {
        return <Navigate to="/auth" replace />;
    }
    return <>{children}</>;
};

const router = createBrowserRouter([
    {
        path: "/auth",
        element: <AuthPage/>,
    },
    {
        path: "/",
        element: (
            <ProtectedRoute>
                <ChatPage/>
            </ProtectedRoute>
        ),
    },
    {
        path: "/chat",
        element: (
            <ProtectedRoute>
                <ChatPage/>
            </ProtectedRoute>
        ),
    },
    {
        path: "/vaults",
        element: (
            <ProtectedRoute>
                <VaultsPage/>
            </ProtectedRoute>
        ),
    },
    {
        path: "/index",
        element: (
            <ProtectedRoute>
                <IndexPage/>
            </ProtectedRoute>
        ),
    },
    {
        path: "/settings",
        element: (
            <ProtectedRoute>
                <SettingsPage/>
            </ProtectedRoute>
        ),
    },
    {
        path: "*",
        element: (
            <Page404/>
        )
    }
]);

export default router;