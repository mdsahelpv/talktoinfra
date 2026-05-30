{{- define "talktoinfra.name" -}}
{{- default .Chart.Name .Values.global.environment | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "talktoinfra.fullname" -}}
{{- printf "%s-%s" .Release.Name .Chart.Name | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "talktoinfra.labels" -}}
app.kubernetes.io/name: {{ include "talktoinfra.name" . }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}

{{- define "talktoinfra.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "talktoinfra.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{- define "talktoinfra.imagePullSecret" -}}
{{- if .Values.global.imageRegistry }}
imagePullSecrets:
  - name: {{ .Values.global.imageRegistry | replace "/" "-" }}-pull-secret
{{- end }}
{{- end }}
