export const TYPE_EXAMPLE = 'example-flow-node'

export interface FlowNodeProps {
    name: string;
    id: string;
    hasInput?: boolean;
    hasOutput?: boolean;
}

export interface FlowNodeItemProps {
    parentId: string;
    selfId: string;
    name?: string;
    hasInput?: boolean;
    hasOutput?: boolean;
}