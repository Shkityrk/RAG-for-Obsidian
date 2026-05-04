import {NavLink} from "react-router-dom";
import { Flex, Text, Button, Drawer, Burger, Stack } from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { IconMessageCircle, IconSettings, IconStack2, IconLogout } from "@tabler/icons-react";
import { getUserData, logout } from "../../utils/auth";
import "./index.css";

const LINKS = [
    {
        title: "Чаты",
        url: "/chat",
        icon: IconMessageCircle,
    },
    {
        title: "Индекс",
        url: "/index",
        icon: IconStack2,
    },
    {
        title: "Настройки",
        url: "/settings",
        icon: IconSettings,
    },
]

export interface BasicLayoutProps  {
    children: React.ReactNode
}


const BasicLayout = (props: BasicLayoutProps) => {
    const userData = getUserData();
    const [mobileMenuOpened, { toggle: toggleMobileMenu, close: closeMobileMenu }] = useDisclosure(false);

    return (
        <div className="app-shell">
            <nav className="navbar">
                <Flex gap="16px" align="center">
                    <NavLink to="/chat" className="navbar__brand" onClick={closeMobileMenu}>
                        <span className="navbar__brand-mark">R</span>
                        <span className="navbar__brand-copy">
                            <span className="navbar__brand-name">RAG Obsidian</span>
                            <span className="navbar__brand-subtitle">Помощник по vault</span>
                        </span>
                    </NavLink>
                </Flex>
                <Flex gap="8px" align="center" className="navbar__links">
                    {
                        LINKS.map(element => {
                            const Icon = element.icon;
                            return (
                            <NavLink 
                                key={element.title} 
                                className={"navbar__link"} 
                                to={element.url} 
                                end
                                onClick={closeMobileMenu}
                            >
                                <Icon size={17} stroke={1.9} />
                                {element.title}
                            </NavLink>
                            );
                        })
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
                                leftSection={<IconLogout size={14} />}
                            >
                                Выйти
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
                title="Меню"
                position="right"
                padding="md"
                size="xs"
            >
                <Stack gap="md">
                    {LINKS.map(element => {
                        const Icon = element.icon;
                        return (
                        <NavLink 
                            key={element.title} 
                            className={"navbar__link-mobile"} 
                            to={element.url} 
                            end
                            onClick={closeMobileMenu}
                        >
                            <Icon size={18} stroke={1.9} />
                            {element.title}
                        </NavLink>
                        );
                    })}
                    {userData && (
                        <>
                            <Text size="sm" c="dimmed">{userData.username}</Text>
                            <Button 
                                variant="light" 
                                size="sm" 
                                onClick={logout}
                                fullWidth
                                leftSection={<IconLogout size={15} />}
                            >
                                Выйти
                            </Button>
                        </>
                    )}
                </Stack>
            </Drawer>
            
            <main className="app-main">
                {props.children}
            </main>
        </div>
    );
}

export default BasicLayout;
