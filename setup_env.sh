#!/bin/bash

echo "Please enter your database credentials:"

read -p "DB_HOST (default: localhost): " DB_HOST
export DB_HOST=${DB_HOST:-localhost}

read -p "DB_NAME (default: cohezion): " DB_NAME
export DB_NAME=${DB_NAME:-cohezion}

read -p "DB_USER (default: postgres): " DB_USER
export DB_USER=${DB_USER:-postgres}

read -sp "DB_PASSWORD: " DB_PASSWORD
export DB_PASSWORD=$DB_PASSWORD
echo

echo "Environment variables set."
