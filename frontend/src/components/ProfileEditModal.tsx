import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Button, Input, Modal, Toast } from "@douyinfe/semi-ui-19";
import { IconClose, IconTick } from "@douyinfe/semi-icons";
import { isAxiosError } from "axios";
import client from "../api/client";

export interface EditableProfile {
  username: string;
  display_name: string | null;
  email: string | null;
}

interface ProfileEditModalProps {
  visible: boolean;
  user: EditableProfile | null;
  onClose: () => void;
  onUpdated: (profile: EditableProfile) => void;
}

export default function ProfileEditModal({
  visible,
  user,
  onClose,
  onUpdated,
}: ProfileEditModalProps) {
  const { t } = useTranslation();
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState({
    username: "",
    display_name: "",
    email: "",
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const checkTimers = useRef<Record<string, ReturnType<typeof setTimeout>>>({});

  useEffect(() => {
    if (!visible || !user) return;
    setForm({
      username: user.username,
      display_name: user.display_name || "",
      email: user.email || "",
    });
    setErrors({});
  }, [user, visible]);

  useEffect(
    () => () => {
      Object.values(checkTimers.current).forEach(clearTimeout);
    },
    [],
  );

  const close = () => {
    setErrors({});
    onClose();
  };

  const checkField = (field: "username" | "email", value: string) => {
    if (checkTimers.current[field]) {
      clearTimeout(checkTimers.current[field]);
    }

    const unchanged =
      (field === "username" && value === user?.username) ||
      (field === "email" && value === (user?.email || ""));
    if (!value || unchanged) {
      setErrors((current) => {
        const next = { ...current };
        delete next[field];
        return next;
      });
      return;
    }

    checkTimers.current[field] = setTimeout(async () => {
      try {
        const response = await client.get("/users/me/check", {
          params: { field, value },
        });
        setErrors((current) => {
          const next = { ...current };
          if (response.data.available) {
            delete next[field];
          } else {
            next[field] =
              field === "username"
                ? t("settings.usernameConflict")
                : t("settings.emailConflict");
          }
          return next;
        });
      } catch {
        // Availability is validated again when the form is submitted.
      }
    }, 300);
  };

  const updateField = (
    field: "username" | "display_name" | "email",
    value: string,
  ) => {
    setForm((current) => ({ ...current, [field]: value }));
    if (field === "username" || field === "email") {
      checkField(field, value);
    }
  };

  const submit = async () => {
    if (Object.keys(errors).length > 0) {
      Toast.warning(t("admin.fixConflicts"));
      return;
    }

    const username = form.username.trim();
    if (!username) {
      Toast.warning(t("settings.usernameRequired"));
      return;
    }

    const updated: EditableProfile = {
      username,
      display_name: form.display_name.trim() || null,
      email: form.email.trim() || null,
    };

    setSubmitting(true);
    try {
      await client.put("/users/me", updated);
      Toast.success(t("settings.saveSuccess"));
      onUpdated(updated);
      window.dispatchEvent(
        new CustomEvent("sharebib-profile-updated", { detail: updated }),
      );
      close();
    } catch (error: unknown) {
      const detail = isAxiosError<{ detail?: string }>(error)
        ? error.response?.data?.detail
        : undefined;
      Toast.error(detail || t("settings.saveFailed"));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal
      className="profile-edit-dialog"
      title={t("settings.editProfile")}
      visible={visible}
      onCancel={close}
      width={500}
      footer={
        <div className="profile-dialog-actions">
          <Button theme="borderless" onClick={close}>
            {t("settings.cancel")}
          </Button>
          <Button
            theme="solid"
            loading={submitting}
            disabled={!form.username.trim() || Object.keys(errors).length > 0}
            onClick={submit}
          >
            {t("settings.save")}
          </Button>
        </div>
      }
    >
      <div className="profile-edit-fields">
        <div>
          <label className="form-label">{t("settings.username")}</label>
          <Input
            value={form.username}
            onChange={(value) => updateField("username", value)}
            suffix={
              errors.username ? (
                <IconClose className="profile-field-icon is-error" />
              ) : form.username && form.username !== user?.username ? (
                <IconTick className="profile-field-icon is-success" />
              ) : null
            }
          />
          {errors.username && (
            <div className="profile-field-error">{errors.username}</div>
          )}
        </div>

        <div>
          <label className="form-label">{t("settings.displayName")}</label>
          <Input
            value={form.display_name}
            onChange={(value) => updateField("display_name", value)}
          />
        </div>

        <div>
          <label className="form-label">{t("settings.email")}</label>
          <Input
            value={form.email}
            onChange={(value) => updateField("email", value)}
            suffix={
              errors.email ? (
                <IconClose className="profile-field-icon is-error" />
              ) : form.email && form.email !== (user?.email || "") ? (
                <IconTick className="profile-field-icon is-success" />
              ) : null
            }
          />
          {errors.email && (
            <div className="profile-field-error">{errors.email}</div>
          )}
        </div>
      </div>
    </Modal>
  );
}
