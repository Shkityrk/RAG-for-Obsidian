import React from 'react'
import ReactDOM from 'react-dom/client'
import {RouterProvider} from "react-router-dom";
import { createTheme, MantineProvider } from '@mantine/core';
import {QueryClient, QueryClientProvider} from '@tanstack/react-query'
// import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { Notifications } from '@mantine/notifications'
import router from "./router";
import './index.css'
import './reset.css'
import '@mantine/core/styles.css';
import '@mantine/charts/styles.css';
import '@mantine/notifications/styles.css';


const theme = createTheme({
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", "Roboto", "Helvetica Neue", Arial, sans-serif',
    defaultRadius: 'md',
    primaryColor: "blue",
    headings: {
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", "Roboto", "Helvetica Neue", Arial, sans-serif',
        fontWeight: '600',
    },
    colors: {
        blue: [
            '#e3f2fd',
            '#bbdefb',
            '#90caf9',
            '#64b5f6',
            '#42a5f5',
            '#2196f3',
            '#1e88e5',
            '#1976d2',
            '#1565c0',
            '#0d47a1',
        ],
    },
    defaultGradient: {
        from: '#4a9eff',
        to: '#2196f3',
        deg: 90,
    },
});

const queryClient = new QueryClient({
    defaultOptions: {
        queries: {
            refetchOnWindowFocus: false,
            retry: 1
        }
    }
});

ReactDOM.createRoot(document.getElementById('root')!).render(
    <React.StrictMode>
        <MantineProvider theme={theme} withGlobalClasses>
            <QueryClientProvider client={queryClient}>
                <Notifications />
                <RouterProvider router={router} />
                {/* <ReactQueryDevtools initialIsOpen /> */}
            </QueryClientProvider>
        </MantineProvider>
    </React.StrictMode>
);
