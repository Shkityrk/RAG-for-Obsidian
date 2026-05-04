import {createBrowserRouter, Navigate} from "react-router-dom";
import {Page404} from "../pages/404";
import {IndexPage} from "../pages/index";
import {AuthPage} from "../pages/auth";
import {ChatPage} from "../pages/chat";
import {SettingsPage} from "../pages/settings";
import {ProtectedRoute} from "./protected-route";

const router = createBrowserRouter([
    {
        path: "/auth",
        element: <AuthPage/>,
    },
    {
        path: "/",
        element: (
            <ProtectedRoute>
                <Navigate to="/index" replace />
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
