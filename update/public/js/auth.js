function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function logout() {
    let response = await fetch('/auth/cookie/logout', {
        method: 'POST'
    });
    let status = response.status;
    if (status === 200) {
        window.location.href = '/';
    } else if (status === 401) {
        document.getElementById('status').innerHTML = 'Ошибка 401: возможно, истек срок действия токена.' +
            ' Обнови страницу';
    }
}

async function login() {
    let username = document.getElementById('floatingInput').value;
    let password = document.getElementById('floatingPassword').value;

    let email = username + '@example.com'

    let params = new URLSearchParams();
    params.set('username', email);
    params.set('password', password);

    let response = await fetch('/auth/cookie/login', {
        method: 'POST',
        body: params
    });
    let status = response.status;
    let json = response.json();

    if (status === 200) {
        window.location.href = '/';
    } else if (status === 400) {
        document.getElementById('status').innerHTML = 'Неверный логин или пароль';
    } else if (status === 422) {
        document.getElementById('status').innerHTML = 'Некорректные значения в полях.';
    }
}
async function change_password_button(token) {
    let password1 = document.getElementById('floatingInput').value;
    let password2 = document.getElementById('floatingPassword').value;
    if (password1 === password2) {
        let data = {
            token: token,
            password: password1
        }
        let response = await fetch('/auth/reset-password', {
            method: 'POST',
            body: JSON.stringify(data),
            headers: {
                'Content-type': 'application/json',
                'accept': 'application/json'
            }
        })
        let status = response.status
        let json = await response.json()
        if (status === 200) {
            document.getElementById('status').innerHTML = 'Успешно. Переадресация...';
            await sleep(1000);
            window.location.href = '/';
        } else if (status === 400) {
            detail = json.detail;
            if (detail === 'RESET_PASSWORD_BAD_TOKEN') {
                document.getElementById('status').innerHTML = 'Некорректный токен. Возможно, он уже устарел.';
            } else if (detail.code === 'RESET_PASSWORD_INVALID_PASSWORD') {
                document.getElementById('status').innerHTML = 'Пароль должен состоять минимум из 3 знаков';
            }
        } else if (status === 422) {
            document.getElementById('status').innerHTML = 'Произошла ошибка.';
        }
    } else {
        document.getElementById('status').innerHTML = 'Пароли не совпадают';
    }

}
async function generate_password_token(email) {
    let data = {email: email}
    let response = await fetch('/auth/forgot-password', {
        method: 'POST',
        body: JSON.stringify(data),
        headers: {
            'Content-type': 'application/json',
            'accept': 'application/json'
        }
    })
    let status = response.status
    let json = await response.json()

    if (status === 202) {
        document.getElementById('status').innerHTML = 'Успешно.';
    } else if (status === 422) {
        document.getElementById('status').innerHTML = 'Произошла ошибка.';
    }
}
async function create_user() {
    let username = document.getElementById('create-input-username').value;
    let group = document.getElementById('create-input-group').value;
    let telegram_username = document.getElementById('create-input-telegram_username').value;
    let vk_username = document.getElementById('create-input-vk_username').value;

    if (username == '') {
        document.getElementById('status').innerHTML = 'Пустое имя пользователя.';
    }
    else if (group == '') {
        document.getElementById('status').innerHTML = 'Пустой номер группы.';
    }
    else if ((telegram_username == '') && (vk_username == '')) {
        document.getElementById('status').innerHTML = 'Не задан ни один идентификатор соцсети.';
    }
    else {
        let data = {
            username: username,
            group: group,
            telegram_username: telegram_username,
            vk_username: vk_username
        }
        let response = await fetch('/auth/register', {
            method: 'POST',
            body: JSON.stringify(data),
            headers: {
                'Content-type': 'application/json',
                'accept': 'application/json'
                }
            })
        let status = response.status
        let json = await response.json()
        if (status === 201) {
            document.getElementById('status').innerHTML = 'Учетная запись успешно создана.';
        } else if (status === 400) {
            document.getElementById('status').innerHTML = 'При создании произошла ошибка 400';
        } else if (status === 422) {
            document.getElementById('status').innerHTML = 'При создании произошла ошибка 422';
        }
    }
}
async function a_user_verification(id) {
    let response = await fetch('/users/'+id)
    let status = response.status
    let json = await response.json()
    if (status === 200) {
        email = json.email;
        is_verified = json.is_verified;
        if (is_verified) {
            document.getElementById('status').innerHTML = 'Пользователь уже верифицирован';
        } else {
            let response_two = await fetch('/auth/request-verify-token', {
            method: 'POST',
            body: JSON.stringify({email: email}),
            headers: {
                'Content-type': 'application/json',
                'accept': 'application/json'
                }
            })
            status = response.status;
            if (status === 202) {
                document.getElementById('status').innerHTML = 'Успешно. Ссылка отправлена в беседу';
            }
        }
    } else if (status === 401) {
        document.getElementById('status').innerHTML = 'Сессия устарела. Обновите страницу';
    } else if (status === 403) {
        document.getElementById('status').innerHTML = 'Доступ запрещен';
    } else if (status === 404) {
        document.getElementById('status').innerHTML = 'Пользователь не найден';
    }
}
async function verify_user(token) {
    let response = await fetch('/auth/verify', {
            method: 'POST',
            body: JSON.stringify({token: token}),
            headers: {
                'Content-type': 'application/json',
                'accept': 'application/json'
                }
            });
    let status = response.status;
    let json = await response.json();
    if (status === 200) {
        document.getElementById('status').innerHTML = 'Верификация пройдена успешно';
    } else if (status === 400) {
        document.getElementById('status').innerHTML = 'Ошибка 400. Возможно, токен устарел';
    } else if (status === 422) {
        document.getElementById('status').innerHTML = 'Ошибка 422';
    }
}
async function edit_user(id) {
    let username = document.getElementById('edit-input-username').value;
    let group = document.getElementById('edit-input-group').value;
    let telegram_username = document.getElementById('edit-input-telegram_username').value;
    let vk_username = document.getElementById('edit-input-vk_username').value;
    let is_verified = document.getElementById('edit-input-is_verified').checked;
    let is_superuser = document.getElementById('edit-input-is_superuser').checked;

    if (telegram_username === '' && vk_username === '') {
        document.getElementById('status').innerHTML = 'Не задан ни один идентификатор соцсети.';
    } else {
        let email = username + '@example.com';
        let response = await fetch('/users/'+id, {
            method: 'PATCH',
            body: JSON.stringify({
                email: email,
                username: username,
                group: group,
                telegram_username: telegram_username,
                vk_username: vk_username,
                is_verified: is_verified,
                is_superuser: is_superuser
            }),
            headers: {
                'Content-type': 'application/json',
                'accept': 'application/json'
                }
            });
        let status = response.status;
        let json = await response.json();
        if (status === 200) {
            document.getElementById('status').innerHTML = 'Успешно';
        } else if (status === 401) {
            document.getElementById('status').innerHTML = 'Сессия устарела. Обновите страницу';
        }
    }
}
async function delete_user(id) {
    let response = await fetch('/users/'+id, {
            method: 'DELETE',
            headers: {
                'Content-type': 'application/json',
                'accept': 'application/json'
                }
            });
    let status = response.status;
    if (status === 204) {
            document.getElementById('status').innerHTML = 'Успешно';
        } else if (status === 401) {
            document.getElementById('status').innerHTML = 'Сессия устарела. Обновите страницу';
        } else if (status === 404) {
            document.getElementById('status').innerHTML = 'Пользователь не найден';
        }
}

