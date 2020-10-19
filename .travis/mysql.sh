#!/usr/bin/env bash
echo "Restart mysql..."
sudo mysql -e "
    use mysql;
    update user set authentication_string=PASSWORD('') where User='root';
    update user set plugin='mysql_native_password';
    FLUSH PRIVILEGES;
    SET @@GLOBAL.wait_timeout=28800;
"