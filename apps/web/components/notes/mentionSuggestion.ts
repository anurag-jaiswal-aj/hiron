import { ReactRenderer } from "@tiptap/react";
import tippy, { Instance, Props } from "tippy.js";
import { MentionList } from "./MentionList";
import { usersApi } from "../../lib/users-api";
import { SuggestionOptions } from "@tiptap/suggestion";

export const mentionSuggestion: Omit<SuggestionOptions, "editor"> = {
  items: async ({ query }) => {
    try {
      const response = await usersApi.listUsers({ isActive: true, limit: 100 });
      return response
        .filter((item) => item.fullName.toLowerCase().startsWith(query.toLowerCase()))
        .slice(0, 5);
    } catch (e) {
      console.error("Failed to fetch users for mention", e);
      return [];
    }
  },

  render: () => {
    let component: ReactRenderer;
    let popup: Instance<Props>[];

    return {
      onStart: (props) => {
        component = new ReactRenderer(MentionList, {
          props,
          editor: props.editor,
        });

        if (!props.clientRect) {
          return;
        }

        popup = tippy("body", {
          getReferenceClientRect: props.clientRect as () => DOMRect,
          appendTo: () => document.body,
          content: component.element,
          showOnCreate: true,
          interactive: true,
          trigger: "manual",
          placement: "bottom-start",
        });
      },

      onUpdate(props) {
        component.updateProps(props);

        if (!props.clientRect) {
          return;
        }

        popup[0].setProps({
          getReferenceClientRect: props.clientRect as () => DOMRect,
        });
      },

      onKeyDown(props) {
        if (props.event.key === "Escape") {
          popup[0].hide();
          return true;
        }
        
        const ref = component.ref as { onKeyDown?: (props: unknown) => boolean };
        return ref?.onKeyDown ? ref.onKeyDown(props) : false;
      },

      onExit() {
        popup[0].destroy();
        component.destroy();
      },
    };
  },
};
