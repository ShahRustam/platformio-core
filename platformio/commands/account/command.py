# Copyright (c) 2014-present PlatformIO <contact@platformio.org>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# pylint: disable=unused-argument

import datetime
import json
import re

import click
from tabulate import tabulate

from platformio.commands.account import exception
from platformio.commands.account.client import AccountClient


@click.group("account", short_help="Manage PIO Account")
def cli():
    pass


def validate_username(value):
    value = str(value).strip()
    if not re.match(r"^[a-z\d](?:[a-z\d]|-(?=[a-z\d])){3,38}$", value, flags=re.I):
        raise click.BadParameter(
            "Invalid username format. "
            "Username must contain at least 4 characters including single hyphens,"
            " and cannot begin or end with a hyphen"
        )
    return value


def validate_email(value):
    value = str(value).strip()
    if not re.match(r"^[a-z\d_.+-]+@[a-z\d\-]+\.[a-z\d\-.]+$", value, flags=re.I):
        raise click.BadParameter("Invalid E-Mail address")
    return value


def validate_password(value):
    value = str(value).strip()
    if not re.match(r"^(?=.*[a-z])(?=.*\d).{8,}$", value):
        raise click.BadParameter(
            "Invalid password format. "
            "Password must contain at least 8 characters"
            " including a number and a lowercase letter"
        )
    return value


@cli.command("register", short_help="Create new PIO Account")
@click.option(
    "-u",
    "--username",
    prompt=True,
    callback=lambda _, __, value: validate_username(value),
)
@click.option(
    "-e", "--email", prompt=True, callback=lambda _, __, value: validate_email(value)
)
@click.option(
    "-p",
    "--password",
    prompt=True,
    hide_input=True,
    confirmation_prompt=True,
    callback=lambda _, __, value: validate_password(value),
)
@click.option("--first-name", prompt=True)
@click.option("--last-name", prompt=True)
def account_register(username, email, password, first_name, last_name):
    client = AccountClient()
    try:
        client.registration(username, email, password, first_name, last_name)
        return click.secho(
            "An account has been successfully created. "
            "Please check your mail to activate your account and verify your email address.",
            fg="green",
        )
    except exception.AccountAlreadyAuthenticated as e:
        return click.secho(str(e), fg="yellow",)


@cli.command("login", short_help="Log in to PIO Account")
@click.option("-u", "--username", prompt="Username or e-mail")
@click.option("-p", "--password", prompt=True, hide_input=True)
def account_login(username, password):
    client = AccountClient()
    try:
        client.login(username, password)
        return click.secho("Successfully logged in!", fg="green")
    except exception.AccountAlreadyAuthenticated as e:
        return click.secho(str(e), fg="yellow",)


@cli.command("logout", short_help="Log out of PIO Account")
def account_logout():
    client = AccountClient()
    try:
        client.logout()
        return click.secho("Successfully logged out!", fg="green")
    except exception.AccountNotAuthenticated as e:
        return click.secho(str(e), fg="yellow",)


@cli.command("password", short_help="Change password")
@click.option("--old-password", prompt=True, hide_input=True)
@click.option("--new-password", prompt=True, hide_input=True, confirmation_prompt=True)
def account_password(old_password, new_password):
    client = AccountClient()
    try:
        client.change_password(old_password, new_password)
        return click.secho("Password successfully changed!", fg="green")
    except exception.AccountNotAuthenticated as e:
        return click.secho(str(e), fg="yellow",)


@cli.command("token", short_help="Get or regenerate Authentication Token")
@click.option("-p", "--password", prompt=True, hide_input=True)
@click.option("--regenerate", is_flag=True)
@click.option("--json-output", is_flag=True)
def account_token(password, regenerate, json_output):
    client = AccountClient()
    try:
        auth_token = client.auth_token(password, regenerate)
        if json_output:
            return click.echo(json.dumps({"status": "success", "result": auth_token}))
        return click.secho("Personal Authentication Token: %s" % auth_token, fg="green")
    except exception.AccountNotAuthenticated as e:
        return click.secho(str(e), fg="yellow",)


@cli.command("forgot", short_help="Forgot password")
@click.option("--username", prompt="Username or e-mail")
def account_forgot(username):
    client = AccountClient()
    client.forgot_password(username)
    return click.secho(
        "If this account is registered, we will send the "
        "further instructions to your E-Mail.",
        fg="green",
    )


@cli.command("update", short_help="Update profile information")
@click.option("--current-password", prompt=True, hide_input=True)
def account_update(current_password):
    client = AccountClient()
    try:
        profile = client.get_profile()
        new_profile = {}
        for field in profile:
            new_profile[field] = click.prompt(
                field.replace("_", " ").capitalize(), default=profile[field]
            )
            if field == "email":
                validate_email(new_profile[field])
            if field == "username":
                validate_username(new_profile[field])
        client.update_profile(new_profile, current_password)
        click.secho("Profile successfully updated!", fg="green")
        username_changed = new_profile["username"] != profile["username"]
        email_changed = new_profile["email"] != profile["email"]
        if not username_changed and not email_changed:
            return None
        try:
            client.logout()
        except exception.AccountNotAuthenticated:
            pass
        if email_changed:
            return click.secho(
                "Please check your mail to verify your new email address and re-login. ",
                fg="yellow",
            )
        return click.secho("Please re-login.", fg="yellow")
    except exception.AccountNotAuthenticated as e:
        return click.secho(str(e), fg="yellow",)


@cli.command("show", short_help="PIO Account information")
@click.option("--offline", is_flag=True)
@click.option("--json-output", is_flag=True)
def account_show(offline, json_output):
    client = AccountClient()
    try:
        info = client.get_account_info(offline)
        if json_output:
            return click.echo(json.dumps(info))
        click.echo()
        if info.get("profile"):
            print_profile(info["profile"])
        if info.get("packages"):
            print_packages(info["packages"])
        if info.get("subscriptions"):
            print_subscriptions(info["subscriptions"])
        return click.echo()
    except exception.AccountNotAuthenticated as e:
        return click.secho(str(e), fg="yellow",)


def print_profile(profile):
    click.secho("Profile", fg="cyan", bold=True)
    click.echo("=" * len("Profile"))
    data = []
    if profile.get("username"):
        data.append(("Username:", profile["username"]))
    if profile.get("email"):
        data.append(("Email:", profile["email"]))
    if profile.get("first_name"):
        data.append(("First name:", profile["first_name"]))
    if profile.get("last_name"):
        data.append(("Last name:", profile["last_name"]))
    click.echo(tabulate(data, tablefmt="plain"))


def print_packages(packages):
    click.echo()
    click.secho("Packages", fg="cyan")
    click.echo("=" * len("Packages"))
    for package in packages:
        click.echo()
        click.secho(package.get("name"), bold=True)
        click.echo("-" * len(package.get("name")))
        if package.get("description"):
            click.echo(package.get("description"))
        data = []
        expire = "-"
        if "subscription" in package:
            expire = datetime.datetime.strptime(
                (
                    package["subscription"].get("end_at")
                    or package["subscription"].get("next_bill_at")
                ),
                "%Y-%m-%dT%H:%M:%SZ",
            ).strftime("%Y-%m-%d")
        data.append(("Expire:", expire))
        services = []
        for key in package:
            if not key.startswith("service."):
                continue
            if isinstance(package[key], dict):
                services.append(package[key].get("title"))
            else:
                services.append(package[key])
        if services:
            data.append(("Services:", ", ".join(services)))
        click.echo(tabulate(data, tablefmt="plain"))


def print_subscriptions(subscriptions):
    click.echo()
    click.secho("Subscriptions", fg="cyan")
    click.echo("=" * len("Subscriptions"))
    for subscription in subscriptions:
        click.echo()
        click.secho(subscription.get("product_name"), bold=True)
        click.echo("-" * len(subscription.get("product_name")))
        data = [("State:", subscription.get("status"))]
        begin_at = datetime.datetime.strptime(
            subscription.get("begin_at"), "%Y-%m-%dT%H:%M:%SZ"
        ).strftime("%Y-%m-%d %H:%M:%S")
        data.append(("Start date:", begin_at or "-"))
        end_at = subscription.get("end_at")
        if end_at:
            end_at = datetime.datetime.strptime(
                subscription.get("end_at"), "%Y-%m-%dT%H:%M:%SZ"
            ).strftime("%Y-%m-%d %H:%M:%S")
        data.append(("End date:", end_at or "-"))
        next_bill_at = subscription.get("next_bill_at")
        if next_bill_at:
            next_bill_at = datetime.datetime.strptime(
                subscription.get("next_bill_at"), "%Y-%m-%dT%H:%M:%SZ"
            ).strftime("%Y-%m-%d %H:%M:%S")
        data.append(("Next payment:", next_bill_at or "-"))
        data.append(
            ("Edit:", click.style(subscription.get("update_url"), fg="blue") or "-")
        )
        data.append(
            ("Cancel:", click.style(subscription.get("cancel_url"), fg="blue") or "-")
        )
        click.echo(tabulate(data, tablefmt="plain"))
