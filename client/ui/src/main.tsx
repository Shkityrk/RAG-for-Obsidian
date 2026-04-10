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
    fontFamily: '"Manrope", "Segoe UI Variable Display", "Segoe UI", "Helvetica Neue", sans-serif',
    defaultRadius: 'lg',
    primaryColor: "mts",
    headings: {
        fontFamily: '"Manrope", "Segoe UI Variable Display", "Segoe UI", "Helvetica Neue", sans-serif',
        fontWeight: '700',
    },
    colors: {
        mts: [
            '#fff0f3',
            '#ffd8e0',
            '#ffb0c0',
            '#ff869f',
            '#ff5b7d',
            '#ff2f5a',
            '#ff0032',
            '#dc002b',
            '#b30023',
            '#8a001b',
        ],
        sky: [
            '#edf4ff',
            '#d5e4ff',
            '#a9c6ff',
            '#7aa8ff',
            '#518dff',
            '#2b7cff',
            '#1269ea',
            '#0a57c4',
            '#01469e',
            '#00347b',
        ],
    },
    defaultGradient: {
        from: '#ff0032',
        to: '#2b7cff',
        deg: 118,
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
