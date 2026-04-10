import {NavLink} from "react-router-dom";
import { Flex, Text, Button, Drawer, Burger, Stack } from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { getUserData, logout } from "../../utils/auth";
import "./index.css";

const LINKS = [
    {
        title: "Chats",
        url: "/chat"
    },
    {
        title: "Index",
        url: "/index"
    },
    {
        title: "Settings",
        url: "/settings"
    },
]

export interface BasicLayoutProps  {
    children: React.ReactNode
}


const BasicLayout = (props: BasicLayoutProps) => {
    const userData = getUserData();
    const [mobileMenuOpened, { toggle: toggleMobileMenu, close: closeMobileMenu }] = useDisclosure(false);

    return (
        <div style={{height: "100vh", display: "flex", flexDirection: "column", backgroundColor: "var(--bg-primary)"}}>
            <nav className="navbar">
                <Flex gap="8px" align="center" className="navbar__links">
                    {
                        LINKS.map(element => (
                            <NavLink 
                                key={element.title} 
                                className={"navbar__link"} 
                                to={element.url} 
                                end
                                onClick={closeMobileMenu}
                            >
                                {element.title}
                            </NavLink>
                        ))
                    }
                </Flex>
                <Flex gap="12px" align="center" className="navbar__user">
                    {userData && (
                        <>
                            <Text size="sm" c="dimmed" className="navbar__username">{userData.username}</Text>
                            <Button 
                                variant="light" 
                                size="xs" 
                                onClick={logout}
                                className="navbar__logout"
                            >
                                Logout
                            </Button>
                        </>
                    )}
                    <Burger
                        opened={mobileMenuOpened}
                        onClick={toggleMobileMenu}
                        className="navbar__burger"
                        size="sm"
                    />
                </Flex>
            </nav>
            
            <Drawer
                opened={mobileMenuOpened}
                onClose={closeMobileMenu}
                title="Menu"
                position="right"
                padding="md"
                size="xs"
            >
                <Stack gap="md">
                    {LINKS.map(element => (
                        <NavLink 
                            key={element.title} 
                            className={"navbar__link-mobile"} 
                            to={element.url} 
                            end
                            onClick={closeMobileMenu}
                        >
                            {element.title}
                        </NavLink>
                    ))}
                    {userData && (
                        <>
                            <Text size="sm" c="dimmed">{userData.username}</Text>
                            <Button 
                                variant="light" 
                                size="sm" 
                                onClick={logout}
                                fullWidth
                            >
                                Logout
                            </Button>
                        </>
                    )}
                </Stack>
            </Drawer>
            
            <main style={{flex: 1, overflow: "auto", backgroundColor: "var(--bg-primary)"}}>
                {props.children}
            </main>
        </div>
    );
}

export default BasicLayout;
