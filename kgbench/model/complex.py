import torch
from kgbench import Config, Dataset
from kgbench.model.kge_model import RelationalScorer, KgeModel


class ComplExScorer(RelationalScorer):
    r"""Implementation of the ComplEx KGE scorer.

    Reference: Théo Trouillon, Johannes Welbl, Sebastian Riedel, Éric Gaussier and
    Guillaume Bouchard: Complex Embeddings for Simple Link Prediction. ICML 2016.
    `<http://proceedings.mlr.press/v48/trouillon16.pdf>`_

    """

    def __init__(self, config: Config, dataset: Dataset, configuration_key=None):
        super().__init__(config, dataset, configuration_key)

    def score_emb(self, s_emb, p_emb, o_emb, combine: str):
        n = p_emb.size(0)

        # Here we use a fast implementation of computing the ComplEx scores using
        # Hadamard products, as in Eq. (11) of paper.
        #
        # Split the relation and object embeddings into real part (first half) and
        # imaginary part (second half).
        p_emb_re, p_emb_im = (t.contiguous() for t in p_emb.chunk(2, dim=1))
        o_emb_re, o_emb_im = (t.contiguous() for t in o_emb.chunk(2, dim=1))

        # combine them again to create a column block for each required combination
        s_all = torch.cat((s_emb, s_emb), dim=1)  # re, im, re, im
        p_all = torch.cat((p_emb_re, p_emb, -p_emb_im), dim=1)  # re, re, im, -im
        o_all = torch.cat((o_emb, o_emb_im, o_emb_re), dim=1)  # re, im, im, re

        if combine == "spo":
            out = (s_all * o_all * p_all).sum(dim=1)
        elif combine == "sp_":
            out = (s_all * p_all).mm(o_all.transpose(0, 1))
        elif combine == "_po":
            out = (p_all * o_all).mm(s_all.transpose(0, 1))
        elif combine == "s_o": 
            n = s_emb.size(0)
            out = (s_all * o_all).mm(p_all.transpose(0, 1))
        else:
            return super().score_emb(s_emb, p_emb, o_emb, combine)

        return out.view(n, -1)

    def score_emb_sp_given_negs(self, s_emb: torch.Tensor , p_emb: torch.Tensor, o_emb: torch.Tensor):
        """ 
            s_emb: batch_size * dim
            p_emb: batch_size * dim
            o_emb: batch_size * negs * dim
         """
        p_emb_re, p_emb_im = (t.contiguous() for t in p_emb.chunk(2, dim=1))
        o_emb_re, o_emb_im = (t.contiguous() for t in o_emb.chunk(2, dim=2))

        # combine them again to create a column block for each required combination
        s_all = torch.cat((s_emb, s_emb), dim=1)  # re, im, re, im
        p_all = torch.cat((p_emb_re, p_emb, -p_emb_im), dim=1)  # re, re, im, -im
        o_all = torch.cat((o_emb, o_emb_im, o_emb_re), dim=2)  # re, im, im, re

        # return ((s_all * p_all).unsqueeze(dim=2) * (o_all.transpose(1,2))).sum(dim=1)
        return torch.bmm(o_all, (s_all * p_all).unsqueeze(dim=2)).squeeze(-1)

    def score_emb_po_given_negs(self, s_emb: torch.Tensor , p_emb: torch.Tensor, o_emb: torch.Tensor):
        """ 
            s_emb: batch_size * negs * dim
            p_emb: batch_size * dim
            o_emb: batch_size * dim
         """
        p_emb_re, p_emb_im = (t.contiguous() for t in p_emb.chunk(2, dim=1))
        o_emb_re, o_emb_im = (t.contiguous() for t in o_emb.chunk(2, dim=1))

        # combine them again to create a column block for each required combination
        s_all = torch.cat((s_emb, s_emb), dim=2)  # re, im, re, im
        p_all = torch.cat((p_emb_re, p_emb, -p_emb_im), dim=1)  # re, re, im, -im
        o_all = torch.cat((o_emb, o_emb_im, o_emb_re), dim=1)  # re, im, im, re

        # return ((s_all.transpose(1,2)) * (o_all * p_all).unsqueeze(dim=2)).sum(dim=1)
        return torch.bmm(s_all, (o_all * p_all).unsqueeze(dim=2)).squeeze(-1)


class ComplEx(KgeModel):
    r"""Implementation of the ComplEx KGE model."""

    def __init__(
        self,
        config: Config,
        dataset: Dataset,
        configuration_key=None,
        init_for_load_only=False,
    ):
        super().__init__(
            config=config,
            dataset=dataset,
            scorer=ComplExScorer,
            configuration_key=configuration_key,
            init_for_load_only=init_for_load_only,
        )
