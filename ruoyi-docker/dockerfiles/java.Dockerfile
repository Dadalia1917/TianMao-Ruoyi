FROM maven:3.9-eclipse-temurin-17-alpine AS builder

WORKDIR /workspace
COPY ruoyi-docker/config/maven-settings.xml /root/.m2/settings.xml
COPY pom.xml ./
COPY ruoyi-common/pom.xml ruoyi-common/pom.xml
COPY ruoyi-system/pom.xml ruoyi-system/pom.xml
COPY ruoyi-framework/pom.xml ruoyi-framework/pom.xml
COPY ruoyi-admin/pom.xml ruoyi-admin/pom.xml
RUN mvn -B -ntp -s /root/.m2/settings.xml -pl ruoyi-admin -am dependency:go-offline -DskipTests

COPY ruoyi-common/src ruoyi-common/src
COPY ruoyi-system/src ruoyi-system/src
COPY ruoyi-framework/src ruoyi-framework/src
COPY ruoyi-admin/src ruoyi-admin/src
RUN mvn -B -ntp -s /root/.m2/settings.xml -pl ruoyi-admin -am clean package -DskipTests

FROM eclipse-temurin:17-jre-alpine

RUN sed -i 's/dl-cdn.alpinelinux.org/mirrors.aliyun.com/g' /etc/apk/repositories \
    && apk add --no-cache curl tzdata \
    && addgroup -S app \
    && adduser -S -G app -h /app app \
    && mkdir -p /app/data/uploadPath /app/logs \
    && chown -R app:app /app

WORKDIR /app
COPY --from=builder --chown=app:app /workspace/ruoyi-admin/target/ruoyi-admin.jar /app/app.jar

USER app
EXPOSE 8080
ENTRYPOINT ["/bin/sh", "-c", "exec java ${JAVA_OPTS} -jar /app/app.jar"]
