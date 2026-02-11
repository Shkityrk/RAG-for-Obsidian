import { isAxiosError } from "axios";
import { ErrorResponse } from "../types/general";
import { notifications } from '@mantine/notifications';


const handleAPIError = (error: unknown) => {
    if (isAxiosError<ErrorResponse>(error)) {
        notifications.show({
            color: "red",
            title: "Error!",
            message: error.response?.data.detail,
            autoClose: 5000,
        })
    } else {
        console.error('Unknown error:', error);
    }
}

export const showErrorNotification = (message: string) => {
    notifications.show({
        title: "Error",
        message: message,
        color: "red",
        autoClose: 5000,
    });
};

export const showSuccessNotification = (message: string) => {
    notifications.show({
        title: "Success",
        message: message,
        color: "green",
        autoClose: 5000,
    });
};

export default handleAPIError;