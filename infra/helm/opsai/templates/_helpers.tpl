{{/* vim: set filetype=mustache: */}}
{{/*
Expand the name of the chart.
*/}}
{{- define "opsai.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "opsai.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- if contains $name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "opsai.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Common labels
*/}}
{{- define "opsai.labels" -}}
helm.sh/chart: {{ include "opsai.chart" . }}
{{ include "opsai.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{/*
Selector labels
*/}}
{{- define "opsai.selectorLabels" -}}
app.kubernetes.io/name: {{ include "opsai.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{/*
Create the name of the service account to use
*/}}
{{- define "opsai.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
    {{ default (include "opsai.fullname" .) .Values.serviceAccount.name }}
{{- else -}}
    {{ default "default" .Values.serviceAccount.name }}
{{- end -}}
{{- end -}}

{{/*
Generate a random JWT secret if not provided
*/}}
{{- define "opsai.jwtSecret" -}}
{{- if .Values.secrets.jwt.secret -}}
{{- .Values.secrets.jwt.secret -}}
{{- else -}}
{{- randAlphaNum 32 -}}
{{- end -}}
{{- end -}}

{{/*
Generate a random DB password if not provided
*/}}
{{- define "opsai.dbPassword" -}}
{{- if .Values.secrets.database.password -}}
{{- .Values.secrets.database.password -}}
{{- else -}}
{{- randAlphaNum 24 -}}
{{- end -}}
{{- end -}}

{{/*
Generate a random admin password if not provided
*/}}
{{- define "opsai.adminPassword" -}}
{{- if .Values.secrets.admin.password -}}
{{- .Values.secrets.admin.password -}}
{{- else -}}
{{- randAlphaNum 16 -}}
{{- end -}}
{{- end -}}

{{/*
Database connection string
*/}}
{{- define "opsai.databaseUrl" -}}
{{- printf "postgresql://%s:%s@%s-postgres:5432/%s" .Values.secrets.database.user (include "opsai.dbPassword" .) (include "opsai.fullname" .) .Values.secrets.database.name -}}
{{- end -}}

{{/*
Redis connection string
*/}}
{{- define "opsai.redisUrl" -}}
{{- printf "redis://%s-redis:6379" (include "opsai.fullname" .) -}}
{{- end -}}

{{/*
Ollama base URL
*/}}
{{- define "opsai.ollamaUrl" -}}
{{- if .Values.ollama.external.enabled -}}
{{- .Values.ollama.external.url -}}
{{- else -}}
{{- printf "http://%s-ollama:11434" (include "opsai.fullname" .) -}}
{{- end -}}
{{- end -}}
