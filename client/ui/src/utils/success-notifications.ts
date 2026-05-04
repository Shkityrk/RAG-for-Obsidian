import { notifications } from '@mantine/notifications';


const notifySuccess = (text: string, title: string = "Успешно") => {
    notifications.show({
        color: "green",
        title: title,
        message: text,
        autoClose: 3000,
    })
}
export default notifySuccess;
