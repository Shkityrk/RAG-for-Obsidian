import { useState, useEffect } from 'react';
import { Container, Paper, TextInput, PasswordInput, Button, Stack, Title, Tabs } from '@mantine/core';
import { useLogin, useRegister } from '../../hooks/auth';
import { isAuthenticated } from '../../utils/auth';
import { useNavigate } from 'react-router-dom';

export const AuthPage = () => {
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [email, setEmail] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const navigate = useNavigate();
  
  const { mutate: login, isPending: isLoginPending } = useLogin();
  const { mutate: register, isPending: isRegisterPending } = useRegister();

  useEffect(() => {
    if (isAuthenticated()) {
      navigate('/index');
    }
  }, [navigate]);

  const handleLogin = () => {
    if (!username || !password) return;
    login({ username, password });
  };

  const handleRegister = () => {
    if (!firstName || !lastName || !email || !username || !password) return;
    register({
      first_name: firstName,
      last_name: lastName,
      email,
      username,
      password,
      user_role: 'client',
    });
  };

  return (
    <Container size="xs" style={{ height: '100vh', display: 'flex', alignItems: 'center' }}>
      <Paper shadow="md" p={30} radius="md" withBorder style={{ width: '100%' }}>
        <Stack gap="md">
          <Title order={2} ta="center">RAG on Obsidian</Title>
          <Tabs defaultValue="login">
            <Tabs.List>
              <Tabs.Tab value="login">Login</Tabs.Tab>
              <Tabs.Tab value="register">Register</Tabs.Tab>
            </Tabs.List>

            <Tabs.Panel value="login" pt="xl">
              <Stack gap="md">
                <TextInput
                  label="Username"
                  placeholder="your_username"
                  required
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                />
                <PasswordInput
                  label="Password"
                  placeholder="Your password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
                <Button
                  fullWidth
                  onClick={handleLogin}
                  loading={isLoginPending}
                  disabled={!username || !password}
                >
                  Login
                </Button>
              </Stack>
            </Tabs.Panel>

            <Tabs.Panel value="register" pt="xl">
              <Stack gap="md">
                <TextInput
                  label="First name"
                  placeholder="John"
                  required
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                />
                <TextInput
                  label="Last name"
                  placeholder="Doe"
                  required
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                />
                <TextInput
                  label="Email"
                  placeholder="your@email.com"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
                <TextInput
                  label="Username"
                  placeholder="your_username"
                  required
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                />
                <PasswordInput
                  label="Password"
                  placeholder="Your password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
                <Button
                  fullWidth
                  onClick={handleRegister}
                  loading={isRegisterPending}
                  disabled={!firstName || !lastName || !email || !username || !password}
                >
                  Register
                </Button>
              </Stack>
            </Tabs.Panel>
          </Tabs>
        </Stack>
      </Paper>
    </Container>
  );
};
