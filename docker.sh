#!/usr/bin/env bash

help=$(cat <<-EOF
Usage: $0 [options]

    -h / --help                     Show this help

Containers:
    up                              run environment (will be build if does not exist)
    build                           build or force rebuild environment
    destroy                         stop and remove containers, networks, images, and volumes
    migrate                         run django migrations
    elastic                         create and populate Elasticsearch index
    admin                           create admin account
    postgres                        run psql commands in the postgres container
    postgres-rm <user_id>           delete selected user from database                    
    purge                           purge unused containers and images
Tests:
    tests                            run tests

EOF
)

case "$1" in

    up)
        docker-compose up
        ;;
    build)
        docker-compose build
        ;;
    destroy)
        docker-compose down -v --rmi local
        ;;
    purge)
        docker rm $(docker ps -aq)
        docker images | grep none | awk '{print "docker rmi " $3;}' | sh
        ;;
    tests)
        docker-compose run --rm simulation python simulation/manage.py test smarthome.tests
        ;;
    migrate)
        docker-compose run --rm simulation python simulation/manage.py makemigrations
        docker-compose run --rm simulation python simulation/manage.py migrate
        ;;
    elastic)
        docker-compose run --rm simulation python simulation/manage.py search_index --rebuild
        ;;
    admin)
        docker-compose run --rm simulation python simulation/manage.py createsuperuser
        ;;
    postgres)
        docker-compose exec postgres psql -U postgres
        ;;
    postgres-rm) #<user_id>
        docker-compose exec postgres psql -U postgres --command "delete from users_user as u where u.id = $2"
        ;;
    start)
        docker-compose build
        docker-compose up  #docker must be up in order to execute the following commands properly
        docker-compose run --rm simulation python simulation/manage.py makemigrations
        docker-compose run --rm simulation python simulation/manage.py migrate
        docker-compose run --rm simulation python simulation/manage.py search_index --rebuild
    ;;
    --help|-h)
        echo "$help"
        ;;
    *)
        echo -e "Unknown parameter $1!"
        echo "$help"
        ;;
esac
